# Phase 3 Follow-Up — Multi-Turn Context & Honest Repair

## Date
2026-08-18

## Scope
This follow-up addresses two specific gaps identified during Phase 3 review:

1. **Fake repair test** — `test_repair_non_watertight_model` monkeypatched `_repair_mesh` instead of exercising the real repair path.
2. **No multi-turn context** — The agent had no mechanism to handle follow-up instructions (e.g. "make it 20% bigger") in the context of an existing session.

---

## Changes Made

### 1. Real Repair Path (test fix)

**File:** `tests/test_agent.py`

**Before:**
- `test_repair_non_watertight_model` monkeypatched `executor._repair_mesh` with a `fake_repair` function that simply copied a pre-made watertight box.
- This did NOT exercise the real `trimesh.fill_holes()` repair logic.

**After:**
- Removed the monkeypatch entirely.
- The test now creates a real broken mesh (box with one face removed), runs the workflow, and asserts:
  - The workflow succeeds via real auto-repair
  - The `analyze_model` step status is `"recovered"`
  - The repaired model file exists and is actually watertight (verified by re-analyzing with `ModelAnalyzer`)

**Verification:**
```
tests/test_agent.py::TestRecoveryPath::test_repair_non_watertight_model PASSED
```

---

### 2. Multi-Turn Context Awareness

**Files modified:**
- `vibe_print/agent/orchestrator.py` — added `handle_follow_up()`, `_parse_follow_up()`, `_execute_scale_follow_up()`
- `vibe_print/models/scaler.py` — added `scale_model()` convenience method
- `vibe_print/server.py` — added `handle_follow_up` MCP tool + `FollowUpInput` schema
- `tests/test_agent.py` — added `TestMultiTurnContext` (4 tests)

#### Supported Follow-Up Patterns

| Pattern | Example | Parsed Action |
|---------|---------|---------------|
| Percent bigger | "make it 20% bigger" | scale_factor = 1.2 |
| Percent smaller | "make it 30% smaller" | scale_factor = 0.7 |
| Scale by multiplier | "scale it by 1.5x" | scale_factor = 1.5 |
| Scale up by | "scale up by 2x" | scale_factor = 2.0 |

**Explicitly NOT supported:** General conversational follow-ups like "make it nicer" — these return a clear error listing supported patterns.

#### Architecture

```
User: "make me a tube squeezer for a 65mm bottle"
  → run_print_workflow() → session stored in SessionStore

User: "make it 20% bigger"
  → handle_follow_up(session_id, "make it 20% bigger")
    → _parse_follow_up() → ("scale", {"scale_factor": 1.2})
    → _execute_scale_follow_up()
      → reads session.model_path
      → calls ModelScaler.scale_model() → new STL
      → re-analyzes → updates session.model_path + session.analysis_result
      → returns structured result with original vs new dimensions
```

#### Session State Updates

After a successful scale follow-up:
- `session.model_path` → points to scaled model
- `session.analysis_result` → updated analysis of scaled model
- `session.messages` → appended with scale confirmation

This means a **third** turn (e.g. "slice it") would operate on the scaled model, not the original.

---

## Test Results

### New Tests (4 added)

| Test | Purpose |
|------|---------|
| `test_scale_follow_up_20_percent_bigger` | End-to-end: workflow → follow-up → verify dimensions scaled ~1.2x |
| `test_scale_follow_up_via_mcp_tool` | Tests the actual `handle_follow_up` MCP server tool |
| `test_unsupported_follow_up_pattern` | "make it nicer" → clear error, not silent failure |
| `test_follow_up_no_model_fails` | Follow-up without model → "No model available" error |

### Full Suite

```
============================ 194 passed in 34.90s =============================
```

- **Previous:** 190 tests (Phase 3 baseline)
- **Now:** 194 tests (+4 new multi-turn tests)
- **All existing tests pass unmodified**

---

## Files Changed

| File | Change |
|------|--------|
| `tests/test_agent.py` | Removed fake repair monkeypatch; added `TestMultiTurnContext` (4 tests) |
| `vibe_print/agent/orchestrator.py` | Added `handle_follow_up()`, `_parse_follow_up()`, `_execute_scale_follow_up()` |
| `vibe_print/models/scaler.py` | Added `scale_model()` convenience method |
| `vibe_print/server.py` | Added `FollowUpInput` schema + `handle_follow_up` MCP tool |

---

## Honest Limitations

1. **Follow-up scope is intentionally narrow.** Only scale instructions are supported. The system does NOT attempt to parse arbitrary conversational context — it returns a clear error for unsupported patterns.

2. **Scale follow-up uses uniform scaling only.** Non-uniform scaling (e.g. "make it taller but keep width") is not yet supported.

3. **No persistent session storage.** Sessions are in-memory only (`SessionStore` dict). Restarting the MCP server loses all session state.

4. **Printer/camera remain simulation-only.** No change to hardware-dependent gaps from Phase 2.5.

---

## Recommendation

The system now supports a genuine multi-turn conversation for the core "generate → scale → (future: slice/print)" flow. This is sufficient for Phase 3 (Intelligent Agent) demonstration. The next logical enhancement would be:

- Add follow-up support for "slice it now" (re-slice the scaled model)
- Add follow-up support for "print it" (start print job from current session)
- Persist sessions to SQLite for cross-restart continuity
