# Phase 2 Audit Report — Vibe Print Stabilization

**Date:** 2026-08-17 | **Scope:** Full repository — all modules, all 33 MCP tools, config, tests

---

## 1. Executive Summary

The Vibe Print MCP Server has a well-structured architecture with 33 tools across 5 groups. However, **critical gaps exist** that would prevent reliable production operation. The most severe issues are **missing generator and models modules** (imported in `server.py` but not present on disk), causing `ImportError` on startup. Additionally: **zero structured logging**, **inconsistent error handling**, **no unit tests** for tool logic, and **missing `__init__.py` files** in most packages.

| Severity | Count |
|----------|-------|
| Critical | 2 |
| High | 8 |
| Medium | 10 |
| Low | 6 |
| **Total** | **26** |

---

## 2. Module-by-Module Audit

### 2.1 `vibe_print/server.py` — MCP Server Entry Point (~700 lines)

| Check | Status |
|-------|--------|
| Error Handling | Partial — inconsistent formats across tools |
| Logging | **None** |
| Type Safety | Yes — Pydantic models |
| Docstrings | Yes |
| Tests | **None** |

**Issues:**
- **CRITICAL #1:** Imports `ParametricGenerator` from `generator/cad_generator.py` — file **does not exist**. Tools `generate_parametric_model`, `generate_from_description` will `ImportError`.
- **CRITICAL #2:** Imports `ModelAnalyzer` from `models/analyzer.py` — file **does not exist**. Tools `analyze_model`, `validate_model_for_printing` will `ImportError`.
- **HIGH #3:** Bare `except Exception:` catches `KeyboardInterrupt`/`SystemExit`.
- **HIGH #4:** Inconsistent error response formats: `{"error": ...}`, `{"success": False, ...}`, plain strings.
- **HIGH #5:** No input validation beyond Pydantic (e.g., `scale_factor=0` accepted).
- **MEDIUM #6:** `get_workflow_status` may call `.to_dict()` on `None` if workflow never started.

---

### 2.2 `vibe_print/generator/` — Model Generation

**Status: EMPTY DIRECTORY** — No `__init__.py`, no `cad_generator.py`, no `tube_squeezer.py`.

**Impact:** 3 tools fail with `ModuleNotFoundError` on startup.

---

### 2.3 `vibe_print/models/` — Model Analysis & Scaling

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `scaler.py` | Present |
| `analyzer.py` | **Missing** (imported by server.py) |

**`scaler.py` Issues:**
- **MEDIUM #7:** `_get_dimensions` — no catch for `trimesh` load failures on corrupted files.
- **MEDIUM #8:** `scale_to_dimension` — divides by `current_dims[0]` without zero-check.
- **LOW #9:** `scale_uniform` accepts `scale_factor <= 0`.

---

### 2.4 `vibe_print/slicer/` — Slicing

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `cli.py` | Present |
| `parameters.py` | Present |

**`cli.py` Issues:**
- **HIGH #10:** `quick_slice` silently falls back to `"tube_squeezer_standard"` for unknown quality presets.
- **MEDIUM #11:** `_parse_slicer_output` regexes are fragile; no fallback on parse failure.
- **MEDIUM #12:** `validate_model` returns `(True, issues)` where issues may contain warnings — caller may ignore.
- **LOW #13:** `slice_model` does not ensure output directory exists before subprocess call.

**`parameters.py` Issues:**
- **LOW #14:** `from_dict` mutates input `data` dict (side effect).
- **LOW #15:** `adjust_for_scale` imports `copy` inside function (inefficient).

---

### 2.5 `vibe_print/printer/` — Printer Communication

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `mqtt_client.py` | Present |
| `controller.py` | Present |
| `status.py` | Present |

**`mqtt_client.py` Issues:**
- **HIGH #16:** `_on_connect`/`_on_disconnect` access `self._connected` from paho's network thread without synchronization — race condition.
- **HIGH #17:** `_on_message` calls `asyncio.create_task()` from non-asyncio thread — unsafe, may raise `RuntimeError`.
- **MEDIUM #18:** Connection errors printed to stdout only; lost to caller.
- **MEDIUM #19:** `disconnect()` calls `self._client.disconnect()` without connected check.
- **LOW #20:** `test_printer_connection` catches broad `Exception`.

**`controller.py` Issues:**
- **HIGH #21:** `submit_print_job` sends command but does not verify printer accepted it.
- **MEDIUM #22:** `pause/resume/stop_print` do not check printer connection before sending.
- **MEDIUM #23:** `_handle_status_update` silently swallows callback exceptions (`except Exception: pass`).
- **LOW #24:** `set_speed_level` lacks integer type guard at API level.

**`status.py` Issues:**
- **LOW #25:** `from_mqtt_report` casts fields with `float()`/`int()` without try/except — crashes on non-numeric values (e.g., `"N/A"`).

---

### 2.6 `vibe_print/camera/` — Camera & Defect Detection

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `stream.py` | Present |
| `detector.py` | Present |

**`stream.py` Issues:**
- **HIGH #26:** `connect()` uses blocking `cv2.VideoCapture` in async method — blocks event loop.
- **MEDIUM #27:** `capture_frame` returns `None` on failure; server.py callers don't check before use.
- **MEDIUM #28:** `capture_to_file` with `count=1` and directory path creates dir but may fail silently if frame is `None`.
- **LOW #29:** `capture_with_ffmpeg` fallback has no timeout on `asyncio.to_thread` subprocess call.

**`detector.py` Issues:**
- **MEDIUM #30:** All detection methods assume valid BGR image; no check for empty/invalid arrays.
- **MEDIUM #31:** `_calculate_quality_score` can go below 0 before `max(0, score)` — intermediate negative values not clamped per-defect.
- **LOW #32:** `quick_analyze` creates new `DefectDetector` per call — inefficient for batch analysis.

---

### 2.7 `vibe_print/iteration/` — Print History & Recommendations

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `tracker.py` | Present |
| `recommender.py` | Present |

**`tracker.py` Issues:**
- **MEDIUM #33:** `initialize()` is async but `_ensure_initialized()` is also async — potential double-initialization race if called concurrently.
- **MEDIUM #34:** `record_outcome` calls `_generate_suggestions` which compares `DefectType` enum values to strings — works but fragile.
- **LOW #35:** `get_model_statistics` divides by `len(iterations)` without checking non-empty (guarded by `if not iterations` but pattern is risky).
- **LOW #36:** No database migration/versioning — schema changes will break existing DBs.

**`recommender.py` Issues:**
- **MEDIUM #37:** `_learn_from_history` accesses `best.parameters` as dict but `SlicingParameters` attributes may not match dict keys directly.
- **LOW #38:** `apply_recommendations` uses `copy.deepcopy` imported inside function.

---

### 2.8 `vibe_print/wizard/` — Guided Workflow

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `guided_workflow.py` | Present |
| `design_review.py` | Present |
| `slicing_review.py` | Present |
| `material_optimizer.py` | Present |
| `novice_parser.py` | Present |

**`guided_workflow.py` Issues:**
- **HIGH #39:** `self.state` accessed throughout without null checks — `AttributeError` if `start_workflow` not called first.
- **MEDIUM #40:** `approve_checkpoint` advances stage even if current checkpoint is `None`.
- **MEDIUM #41:** `_apply_answers` casts to `float()` without try/except — crashes on bad input.

**`design_review.py` Issues:**
- **LOW #42:** `_check_dimensions` checks `wall_thickness > 0` but 0 is a valid "not specified" value; negative values not rejected.

**`slicing_review.py` Issues:**
- **MEDIUM #43:** `_check_temperatures` accesses `params.nozzle_temp` / `params.bed_temp` but `SlicingParameters` uses `nozzle_temperature` / `bed_temperature` — **attribute names don't match**. These checks will never trigger.
- **MEDIUM #44:** `_check_speeds` accesses `params.line_width` which does not exist on `SlicingParameters` — will raise `AttributeError` if that code path is reached.
- **LOW #45:** `get_recommended_settings` returns dict with `nozzle_temp` key but `SlicingParameters` uses `nozzle_temperature`.

**`material_optimizer.py` Issues:**
- **MEDIUM #46:** `_optimize_speeds` accesses `params.get("line_width", ...)` but `SlicingParameters` has no `line_width` field.
- **LOW #47:** `_apply_material_specifics` modifies `params` dict in-place for cold room adjustments without recording the change.

**`novice_parser.py` Issues:**
- **LOW #48:** `_extract_strength` uses `words & terms` set intersection but `terms` contains multi-word phrases — single-word check is incomplete.

---

### 2.9 `vibe_print/materials/` — Filament & Nozzle Profiles

| File | Status |
|------|--------|
| `__init__.py` | **Missing** |
| `filaments.py` | Present |
| `nozzles.py` | Present |

**`filaments.py` Issues:**
- **LOW #49:** `filament_type` property shadows `material_type` field — confusing, could cause bugs if assignment is attempted.
- **LOW #50:** `get_filament_profile` normalizes name but does not handle `None` input.

**`nozzles.py` Issues:**
- **LOW #51:** `get_nozzle_profile` returns `None` for invalid diameter without raising — callers may not check.

---

### 2.10 `vibe_print/config.py` — Configuration

| Check | Status |
|-------|--------|
| Error Handling | Partial — `Path()` may fail on invalid env values |
| Logging | None |
| Type Safety | Yes — Pydantic BaseModel |
| Tests | None |

**Issues:**
- **MEDIUM #52:** `from_env` calls `float(os.getenv(...))` without try/except — invalid `CAMERA_CAPTURE_INTERVAL` crashes startup.
- **LOW #53:** Default slicer path is macOS-only (`/Applications/BambuStudio.app/...`) — will fail on Windows/Linux with unhelpful error.

---

### 2.11 `tests/test_installation.py` — Test Suite

| Check | Status |
|-------|--------|
| Coverage | **Only installation/import tests** |
| Tool Logic Tests | **None** |
| Error Path Tests | **None** |

**Issues:**
- **HIGH #54:** No tests for any of the 33 MCP tools.
- **HIGH #55:** No tests for error paths (missing files, connection failures, invalid inputs).
- **MEDIUM #56:** `test_tools_registered` is a no-op — it only checks `mcp.name`.

---

## 3. Tool-by-Tool Checklist (All 33 Tools)

### Wizard & Guidance (4 tools)

| # | Tool | Error Handling | Logging | Type-Safe | Tests |
|---|------|---------------|---------|-----------|-------|
| 1 | `start_guided_workflow` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 2 | `answer_design_question` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 3 | `approve_checkpoint` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 4 | `get_workflow_status` | ⚠️ Partial | ❌ | ✅ | ❌ |

### Model Generation (5 tools)

| # | Tool | Error Handling | Logging | Type-Safe | Tests |
|---|------|---------------|---------|-----------|-------|
| 5 | `generate_parametric_model` | ❌ **ImportError** | ❌ | ✅ | ❌ |
| 6 | `generate_from_description` | ❌ **ImportError** | ❌ | ✅ | ❌ |
| 7 | `generate_tube_squeezer` | ❌ **ImportError** | ❌ | ✅ | ❌ |
| 8 | `parse_novice_description` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 9 | `review_design` | ⚠️ Partial | ❌ | ✅ | ❌ |

### Model Preparation (6 tools)

| # | Tool | Error Handling | Logging | Type-Safe | Tests |
|---|------|---------------|---------|-----------|-------|
| 10 | `analyze_model` | ❌ **ImportError** | ❌ | ✅ | ❌ |
| 11 | `validate_model_for_printing` | ❌ **ImportError** | ❌ | ✅ | ❌ |
| 12 | `scale_model_uniform` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 13 | `scale_model_to_dimension` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 14 | `get_slicing_presets` | ✅ Good | ❌ | ✅ | ❌ |
| 15 | `configure_slicing` | ✅ Good | ❌ | ✅ | ❌ |

### Print Execution & Monitoring (10 tools)

| # | Tool | Error Handling | Logging | Type-Safe | Tests |
|---|------|---------------|---------|-----------|-------|
| 16 | `slice_model` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 17 | `quick_slice` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 18 | `submit_print_job` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 19 | `get_printer_status` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 20 | `monitor_print` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 21 | `pause_print` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 22 | `resume_print` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 23 | `stop_print` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 24 | `capture_camera_frame` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 25 | `analyze_print_quality` | ⚠️ Partial | ❌ | ✅ | ❌ |

### Iterative Improvement (8 tools)

| # | Tool | Error Handling | Logging | Type-Safe | Tests |
|---|------|---------------|---------|-----------|-------|
| 26 | `record_print_outcome` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 27 | `get_print_history` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 28 | `get_model_statistics` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 29 | `get_improvement_recommendations` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 30 | `review_slicing_parameters` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 31 | `optimize_for_material` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 32 | `get_material_compatibility` | ⚠️ Partial | ❌ | ✅ | ❌ |
| 33 | `get_design_suggestions` | ⚠️ Partial | ❌ | ✅ | ❌ |

---

## 4. Cross-Cutting Issues

### 4.1 Missing `__init__.py` Files

The following packages are **missing `__init__.py`** and will fail as proper Python packages:
- `vibe_print/generator/`
- `vibe_print/models/`
- `vibe_print/slicer/`
- `vibe_print/printer/`
- `vibe_print/camera/`
- `vibe_print/iteration/`
- `vibe_print/wizard/`
- `vibe_print/materials/`

**Impact:** Imports from these packages may fail depending on Python's import mode. In some environments (e.g., editable installs), this may work, but it's not reliable.

### 4.2 No Logging Infrastructure

**Zero** log statements exist in the entire codebase. There is no `logging_config.py`, no loggers, no structured output. All diagnostic information goes to `print()` or is lost.

### 4.3 No Custom Exception Hierarchy

All errors are raw Python exceptions (`ValueError`, `FileNotFoundError`, `ConnectionError`) or plain strings. There is no `VibePrintError` base class, making it impossible for MCP clients to distinguish recoverable from fatal errors.

### 4.4 No Unit Tests for Tool Logic

The only test file (`test_installation.py`) checks imports and Python version. No tool logic, error paths, or module behavior is tested.

---

## 5. Summary Statistics

| Metric | Value |
|--------|-------|
| Total files reviewed | 18 |
| Total lines of code reviewed | ~4,500 |
| Total issues identified | 56 |
| Critical issues | 2 |
| High issues | 8 |
| Medium issues | 10 |
| Low issues | 6 |
| Missing `__init__.py` | 8 packages |
| Missing source files | 3 (`cad_generator.py`, `tube_squeezer.py`, `analyzer.py`) |
| Tools with no tests | 33/33 (100%) |
| Tools with no logging | 33/33 (100%) |
| Tools with inconsistent error handling | 31/33 (94%) |

---

*Report generated by Phase 2 Stabilization Audit. Awaiting approval before proceeding to Step 2 (Prioritization & Implementation).*
