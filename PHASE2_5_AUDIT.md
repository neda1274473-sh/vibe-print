# Phase 2.5 Audit — 33 MCP Tools Gap Analysis

## Environment Status

| Dependency | Status | Notes |
|------------|--------|-------|
| Python | 3.12 | OK |
| trimesh | 5.0.0 | OK — used by analyzer, scaler |
| CadQuery | NOT INSTALLED | `cadquery-ocp` not available; code has graceful fallback |
| OpenSCAD | NOT INSTALLED | `openscad` binary not found; code has graceful fallback |
| OpenCV | NOT INSTALLED | `cv2` not available; detector raises ImportError |
| PrusaSlicer/BambuStudio CLI | NOT INSTALLED | `SlicerCLI` will use mock mode |
| MQTT (paho) | NOT INSTALLED | `BambuMQTTClient` will use simulation mode |
| SQLite | Built-in | OK — iteration tracker works |
| pytest | OK | 103 tests passing |

## Current Module Maturity

| Module | Maturity | Key Classes |
|--------|----------|-------------|
| `exceptions.py` | ✅ Production | Full typed hierarchy with `.to_dict()` |
| `logging_config.py` | ✅ Production | Structured JSON logging |
| `generator/requirements.py` | ✅ Real | `RequirementsParser`, `ModelRequirements` |
| `generator/cad_generator.py` | ⚠️ Partial | Real CadQuery code, but **fallback creates empty placeholder files** when CQ unavailable |
| `generator/parametric.py` | ✅ Real | Full `ParametricGenerator` with 5 category generators |
| `generator/templates.py` | ✅ Real | `TemplateLibrary` with `TubeSqueezerTemplate` (real CQ), `PhoneHolderTemplate`, `CableCatchTemplate` |
| `models/analyzer.py` | ✅ Real | `ModelAnalyzer` with trimesh — fully functional |
| `models/scaler.py` | ✅ Real | `ModelScaler` with trimesh — fully functional |
| `slicer/cli.py` | ⚠️ Partial | `SlicerCLI` calls external binary; needs mock mode |
| `slicer/parameters.py` | ✅ Real | `SlicingParameters`, 4 presets, `adjust_for_scale()` |
| `printer/mqtt_client.py` | ⚠️ Partial | Real MQTT logic but no simulation mode |
| `printer/controller.py` | ✅ Real | `PrinterController` with full job lifecycle |
| `printer/status.py` | ✅ Real | `PrinterStatus`, `PrinterState`, `PrintProgress` |
| `camera/stream.py` | ⚠️ Partial | RTSP logic but no simulation mode |
| `camera/detector.py` | ✅ Real | `DefectDetector` with 5 CV algorithms (needs cv2) |
| `iteration/tracker.py` | ✅ Real | `IterationTracker` with SQLite backend |
| `iteration/recommender.py` | ✅ Real | `ParameterRecommender` with heuristic rules |
| `materials/` | ❌ Empty | No implementation |
| `wizard/` | ❌ Empty | No implementation |
| `server.py` | ❌ Empty | **Zero MCP tools registered** |

---

## The 33 Tools — Gap Audit

### Group 1: Wizard & Guidance (4 tools)

| # | Tool Name | Status | Reason |
|---|-----------|--------|--------|
| 1 | `vibe_suggest_model` | **(b) Needs new logic** | `wizard/` module is empty; needs minimal heuristic suggester |
| 2 | `vibe_estimate_print_time` | **(b) Needs new logic** | No estimator module exists; build heuristic estimator from volume + params |
| 3 | `vibe_check_printer_compatibility` | **(a) Fully implementable** | Use `ModelAnalyzer` dimensions + known bed sizes |
| 4 | `vibe_get_printing_guide` | **(b) Needs new logic** | `wizard/` empty; build static guide lookup |

### Group 2: Model Generation (5 tools)

| # | Tool Name | Status | Reason |
|---|-----------|--------|--------|
| 5 | `vibe_parse_requirements` | **(a) Fully implementable** | `RequirementsParser` is real and tested |
| 6 | `vibe_generate_parametric` | **(a) Fully implementable** | `ParametricGenerator.generate_from_requirements()` is real |
| 7 | `vibe_generate_from_template` | **(a) Fully implementable** | `TemplateLibrary.generate_from_template()` is real |
| 8 | `vibe_list_templates` | **(a) Fully implementable** | `TemplateLibrary.list_templates()` is real |
| 9 | `vibe_analyze_reference_image` | **(c) Out of scope** | Requires CV + calibration logic not built; flag with TODO |

*Note: `vibe_ai_generate` and `vibe_ai_status` from the examples are **not** in the original 33-count. They require external API keys and services. The 5 tools above are the core generation set.*

### Group 3: Model Preparation (6 tools)

| # | Tool Name | Status | Reason |
|---|-----------|--------|--------|
| 10 | `vibe_analyze_model` | **(a) Fully implementable** | `ModelAnalyzer.analyze()` is real and tested |
| 11 | `vibe_scale_model` | **(a) Fully implementable** | `ModelScaler.scale_uniform()` / `scale_for_tube_squeezer()` are real |
| 12 | `vibe_slice_model` | **(a) Fully implementable** | `SlicerCLI.slice()` exists; add mock mode for this env |
| 13 | `vibe_list_presets` | **(a) Fully implementable** | `BUILTIN_PRESETS` dict is real |
| 14 | `vibe_get_preset_details` | **(a) Fully implementable** | Wrap `get_preset()` from parameters.py |
| 15 | `vibe_adjust_parameters_for_scale` | **(a) Fully implementable** | `adjust_for_scale()` exists in parameters.py |

### Group 4: Print Execution & Monitoring (10 tools)

| # | Tool Name | Status | Reason |
|---|-----------|--------|--------|
| 16 | `vibe_test_printer_connection` | **(a) Fully implementable** | `BambuMQTTClient.connect()` + simulation mode |
| 17 | `vibe_get_printer_status` | **(a) Fully implementable** | `PrinterController.refresh_status()` + simulation mode |
| 18 | `vibe_submit_print_job` | **(a) Fully implementable** | `PrinterController.submit_print_job()` + simulation mode |
| 19 | `vibe_control_print` | **(a) Fully implementable** | `PrinterController.pause/resume/stop()` + simulation mode |
| 20 | `vibe_set_print_speed` | **(a) Fully implementable** | `PrinterController.set_speed_level()` + simulation mode |
| 21 | `vibe_set_nozzle_temp` | **(a) Fully implementable** | `PrinterController.set_nozzle_temp()` + simulation mode |
| 22 | `vibe_set_bed_temp` | **(a) Fully implementable** | `PrinterController.set_bed_temp()` + simulation mode |
| 23 | `vibe_send_gcode` | **(a) Fully implementable** | `PrinterController.send_gcode()` + simulation mode |
| 24 | `vibe_home_axes` | **(a) Fully implementable** | `PrinterController.home_axes()` + simulation mode |
| 25 | `vibe_capture_camera` | **(a) Fully implementable** | `CameraStream.capture_frame()` + simulation mode |
| 26 | `vibe_analyze_print_quality` | **(a) Fully implementable** | `DefectDetector.analyze_frame()` + simulation mode (returns no-defect result when cv2 unavailable) |

### Group 5: Iterative Improvement (8 tools)

| # | Tool Name | Status | Reason |
|---|-----------|--------|--------|
| 27 | `vibe_create_iteration` | **(a) Fully implementable** | `IterationTracker.create_iteration()` is real |
| 28 | `vibe_record_outcome` | **(a) Fully implementable** | `IterationTracker.record_outcome()` is real |
| 29 | `vibe_get_recommendations` | **(a) Fully implementable** | `ParameterRecommender.get_recommendations()` is real |
| 30 | `vibe_apply_recommendations` | **(a) Fully implementable** | `ParameterRecommender.apply_recommendations()` is real |
| 31 | `vibe_get_model_history` | **(a) Fully implementable** | `IterationTracker.get_iterations_for_model()` is real |
| 32 | `vibe_compare_iterations` | **(b) Needs new logic** | No comparison utility exists; build simple diff |
| 33 | `vibe_export_iteration_report` | **(b) Needs new logic** | No report exporter exists; build JSON/MD exporter |

---

## Summary Counts

| Category | Count | (a) Implementable | (b) Needs New Logic | (c) Out of Scope |
|----------|-------|-------------------|---------------------|------------------|
| Wizard & Guidance | 4 | 1 | 3 | 0 |
| Model Generation | 5 | 4 | 0 | 1 |
| Model Preparation | 6 | 6 | 0 | 0 |
| Print Execution & Monitoring | 10 | 10 | 0 | 0 |
| Iterative Improvement | 8 | 6 | 2 | 0 |
| **Total** | **33** | **27** | **5** | **1** |

## Critical Gaps to Close This Phase

1. **server.py is empty** — must register all 33 tools with Pydantic schemas
2. **CadQuery not installed** — must ensure trimesh-based generation produces valid STLs for tube_squeezer (the `cad_generator.py` fallback creates empty files)
3. **Slicer CLI not available** — must add labeled mock mode
4. **MQTT/RTSP not available** — must add labeled simulation mode
5. **wizard/ empty** — must build minimal heuristic logic for 3 tools
6. **iteration/ missing compare/export** — must build minimal utilities

## CadQuery Replacement Strategy

Since CadQuery is not installed in this environment, the tube squeezer generation will use **trimesh** to build valid manifold geometry programmatically. This is a real geometric construction (not a placeholder tetrahedron) — it builds:
- A solid box
- Subtracts a slot
- Adds grip features
- Exports valid STL

The `generator/cad_generator.py` stub will be replaced with a `trimesh`-based generator that produces the same parametric tube squeezer geometry. When CadQuery IS available (user's machine), the existing `parametric.py` and `templates.py` code already works. The new trimesh-based generator serves as the **reliable fallback** that never produces empty files.

## Mock/Simulation Mode Policy

Every mock or simulation path will be:
- Clearly labeled with `# SIMULATION MODE` comment in code
- Return a `simulated: true` flag in the response dict
- Documented in the final report

Never present simulation output as real hardware output.
