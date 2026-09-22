# Vibe Print — Capability Audit

**Date:** 2026-08-22
**Commit:** 867d58bd8a97875cc77e661c47f6b934f35cd5a2
**Method:** Pure observation and live testing. No code was modified.

---

## Part 1 — The Real Capability Map (from actual code)

### 1.1 ObjectCategory values in `requirements.py`

The `ObjectCategory` enum (line 18–27) defines **8** categories:

| Enum Member | Value | Has Generator in `cad_generator.py`? |
|-------------|-------|--------------------------------------|
| `BOX` | `"box"` | ✅ `_generate_box` |
| `CYLINDER` | `"cylinder"` | ✅ `_generate_cylinder` |
| `TUBE_SQUEEZER` | `"tube_squeezer"` | ✅ `_generate_tube_squeezer` |
| `BRACKET` | `"bracket"` | ✅ `_generate_bracket` |
| `ENCLOSURE` | `"enclosure"` | ✅ `_generate_enclosure` |
| `SPACER` | `"spacer"` | ✅ `_generate_spacer` |
| `HOOK` | `"hook"` | ✅ `_generate_hook` |
| `CUSTOM` | `"custom"` | ⚠️ Falls back to `box` generator (line 173 in `cad_generator.py`) |

**Verdict:** Every non-custom category has a working 1:1 generator function. `CUSTOM` is explicitly mapped to the `box` generator as a fallback.

### 1.2 CATEGORY_KEYWORDS dictionary (exact contents from `requirements.py` lines 157–193)

```python
CATEGORY_KEYWORDS: Dict[ObjectCategory, List[str]] = {
    ObjectCategory.TUBE_SQUEEZER: [
        "tube squeezer", "toothpaste squeezer", "lotion squeezer",
        "squeezer", "squeeze", "toothpaste", "lotion",
        "cream", "paste", "dispenser", "roller", "wringer"
    ],
    ObjectCategory.BRACKET: [
        "monitor stand", "shelf bracket", "wall mount", "corner brace",
        "bracket", "mounting", "mount", "stand",
        "brace", "L-shaped", "L bracket"
    ],
    ObjectCategory.ENCLOSURE: [
        "electronics box", "project box", "raspberry pi",
        "arduino", "compartment", "cavity",
        "enclosure", "housing", "case", "container",
        "hollow", "lid", "storing", "inside", "shell", "cover"
    ],
    ObjectCategory.BOX: [
        "rectangular prism", "calibration cube", "test cube",
        "solid block", "solid box", "no lid",
        "box"
    ],
    ObjectCategory.CYLINDER: [
        "cylindrical rod", "round rod",
        "cylinder", "rod", "peg", "disc", "disk", "pin", "shaft",
        "round", "tube"  # "tube" is ambiguous but cylinder is the safer fallback
    ],
    ObjectCategory.SPACER: [
        "spacer washer", "spacer ring",
        "standoff", "bushing", "grommet",
        "spacer", "washer", "pcb"
    ],
    ObjectCategory.HOOK: [
        "wall hook", "coat hook",
        "hook", "hanger", "clip", "clamp", "grip", "grabber"
    ],
}
```

**Note:** `CUSTOM` has **zero keywords**. It is only reached when no other category scores.

### 1.3 MCP tools registered in `server.py`

The file header claims "33 real tools." Here is the actual inventory with one-line descriptions:

#### Wizard & Guidance (4 tools)
1. `suggest_model` — Suggest model type from natural language description.
2. `estimate_print_time` — Estimate print time and filament usage.
3. `check_printer_compatibility` — Check if model fits on printer bed.
4. `get_printing_guide` — Get printing guide for a model category.

#### Model Generation (5 tools)
5. `generate_model` — Generate parametric 3D model from explicit type and parameters.
6. `generate_from_description` — Generate model from natural language description (parses + routes + generates).
7. `analyze_model` — Analyze a 3D model file (dimensions, volume, manifold check).
8. `scale_model` — Scale a model uniformly or to target dimensions.
9. `export_model` — Export model to a different format (stl, obj, 3mf) — currently just copies the file.

#### Model Preparation (6 tools)
10. `slice_model` — Slice a model and produce G-code / 3MF (falls back to MockSlicerCLI if no real slicer is installed).
11. `validate_model` — Validate model for printability (checks watertight and volume > 0).
12. `get_slicing_profiles` — List available slicing quality profiles (hardcoded list).
13. `estimate_slicing` — Estimate slicing time and output file size (heuristic based on volume).
14. `preview_gcode` — Preview first N lines of a G-code file.
15. `repair_model` — Attempt to repair a non-manifold model using trimesh `fill_holes`.

#### Print Execution & Monitoring (10 tools)
16. `connect_printer` — Connect to printer via MQTT.
17. `disconnect_printer` — Disconnect from printer.
18. `get_printer_status` — Get current printer status.
19. `start_print` — Start a print job from G-code file.
20. `pause_print` — Pause current print.
21. `resume_print` — Resume paused print.
22. `cancel_print` — Cancel current print.
23. `connect_camera` — Connect to printer camera stream.
24. `capture_frame` — Capture a single camera frame.
25. `get_camera_status` — Get camera connection status.

#### Iterative Improvement (8 tools)
26. `create_iteration` — Create a new print iteration record.
27. `record_outcome` — Record the outcome of a print attempt.
28. `get_iteration_history` — Get print iteration history (requires API key auth).
29. `compare_iterations` — Compare two print iterations.
30. `get_improvement_recommendations` — Get improvement recommendations based on iteration history.
31. `export_history` — Export iteration history to JSON file.
32. `get_model_statistics` — Get aggregate statistics for a model's print history.
33. `analyze_quality` — Analyze print quality from an image (SIMULATION MODE if no image provided; real CV not implemented).

#### Agent Workflow (1 tool)
34. `run_print_workflow` — Run a complete print workflow from goal to print-ready output (agent parses, generates, analyzes, validates, slices, records).
35. `handle_follow_up` — Handle a follow-up instruction in the context of an existing session (supports only explicit scale-up/scale-down patterns).
36. `get_print_analytics` — Get structured analytics on print workflows, failures, and performance.

#### Scale & Cloud (1 tool)
37. `get_server_status` — Get server health and runtime status.
38. `sync_to_cloud` — Sync local data to cloud (simulated: second local SQLite DB).

#### Fleet / Multi-Printer Management (7 tools)
39. `connect_fleet_printer` — Connect a printer to the fleet with a unique printer_id.
40. `disconnect_fleet_printer` — Disconnect a printer from the fleet by printer_id.
41. `list_printers` — List all connected printers in the fleet.
42. `get_fleet_printer_status` — Get status for a specific printer in the fleet.
43. `start_fleet_print` — Start a print job on a specific printer in the fleet.
44. `pause_fleet_print` — Pause a print job on a specific printer in the fleet.
45. `resume_fleet_print` — Resume a paused print job on a specific printer in the fleet.
46. `cancel_fleet_print` — Cancel a print job on a specific printer in the fleet.

**Actual count:** 46 tool functions are decorated with `@mcp.tool()`. The "33" in the header appears to be stale documentation.

---

## Part 2 — Test with Real English Requests

All 10 requests were run through `generate_from_description()` on a live system with CadQuery available. Below are the **exact** inputs, detected categories, detected dimensions/parameters, and generation outcomes.

---

### Test 1: "I need a small box to store screws, about 80mm wide"

- **Detected category:** `box`
- **Detected dimensions:** `[Dimension(value=80.0, unit='mm', context='wide', is_target=True)]`
- **Extracted numbers:** `[80.0]`
- **Generated name:** `box_80mm`
- **Generated description:** `A box (80mm)`
- **Generation result:** ✅ SUCCESS
- **Model type:** `box`
- **Parameters:** `{'width': 80.0, 'height': 48.0, 'depth': 64.0}`
- **Output:** `from_description.stl` (80.0 × 64.0 × 48.0 mm)

---

### Test 2: "Can you make a cup holder that clips onto a car vent"

- **Detected category:** `custom`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `custom`
- **Generated description:** `A custom`
- **Generation result:** ⚠️ SUCCESS (but misrouted to fallback)
- **Model type:** `box` (fallback because category = custom)
- **Parameters:** `{'width': 50, 'height': 30.0, 'depth': 40.0}`
- **Output:** `from_description.stl` (50.0 × 40.0 × 30.0 mm) — a generic box, not a cup holder

---

### Test 3: "I want a phone stand that holds my phone at an angle"

- **Detected category:** `bracket`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `bracket`
- **Generated description:** `A bracket`
- **Generation result:** ✅ SUCCESS (routed to bracket)
- **Model type:** `bracket`
- **Parameters:** `{'width': 60, 'height': 48.0, 'thickness': 2.0, 'hole_diameter': 5.0}`
- **Output:** `from_description.stl` (60.0 × 48.0 × 2.0 mm) — an L-bracket, not a phone stand

---

### Test 4: "Make me a keychain with a hole for a ring"

- **Detected category:** `custom`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `ring_custom`
- **Generated description:** `A custom for ring`
- **Generation result:** ⚠️ SUCCESS (but misrouted to fallback)
- **Model type:** `box` (fallback because category = custom)
- **Parameters:** `{'width': 50, 'height': 30.0, 'depth': 40.0}`
- **Output:** `from_description.stl` (50.0 × 40.0 × 30.0 mm) — a generic box, not a keychain

---

### Test 5: "I need a cable clip to hold a USB cable to my desk"

- **Detected category:** `hook`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `hook`
- **Generated description:** `A hook`
- **Generation result:** ✅ SUCCESS (routed to hook)
- **Model type:** `hook`
- **Parameters:** `{'arm_length': 40, 'thickness': 2.0, 'mount_hole_diameter': 5.0}`
- **Output:** `from_description.stl` (arm 40.0 mm) — a wall hook, not a cable clip

---

### Test 6: "Design a simple gear with 20 teeth"

- **Detected category:** `custom`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[20.0]`
- **Generated name:** `custom`
- **Generated description:** `A custom`
- **Generation result:** ⚠️ SUCCESS (but misrouted to fallback)
- **Model type:** `box` (fallback because category = custom)
- **Parameters:** `{'width': 50, 'height': 30.0, 'depth': 40.0}`
- **Output:** `from_description.stl` (50.0 × 40.0 × 30.0 mm) — a generic box, not a gear

---

### Test 7: "I want a vase, about 100mm tall"

- **Detected category:** `custom`
- **Detected dimensions:** `[Dimension(value=100.0, unit='mm', context='tall', is_target=True)]`
- **Extracted numbers:** `[100.0]`
- **Generated name:** `custom_100mm`
- **Generated description:** `A custom (100mm)`
- **Generation result:** ⚠️ SUCCESS (but misrouted to fallback)
- **Model type:** `box` (fallback because category = custom)
- **Parameters:** `{'width': 100.0, 'height': 60.0, 'depth': 80.0}`
- **Output:** `from_description.stl` (100.0 × 80.0 × 60.0 mm) — a generic box, not a vase

---

### Test 8: "Make a name tag holder with a pin clip"

- **Detected category:** `hook`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `hook`
- **Generated description:** `A hook`
- **Generation result:** ✅ SUCCESS (routed to hook)
- **Model type:** `hook`
- **Parameters:** `{'arm_length': 40, 'thickness': 2.0, 'mount_hole_diameter': 5.0}`
- **Output:** `from_description.stl` (arm 40.0 mm) — a wall hook, not a name tag holder

---

### Test 9: "I need a wall mount for my router"

- **Detected category:** `bracket`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `router_bracket`
- **Generated description:** `A bracket for router`
- **Generation result:** ✅ SUCCESS (routed to bracket)
- **Model type:** `bracket`
- **Parameters:** `{'width': 60, 'height': 48.0, 'thickness': 2.0, 'hole_diameter': 5.0}`
- **Output:** `from_description.stl` (60.0 × 48.0 × 2.0 mm) — an L-bracket, arguably the closest available shape

---

### Test 10: "Create a puzzle piece shape"

- **Detected category:** `custom`
- **Detected dimensions:** `[]`
- **Extracted numbers:** `[]`
- **Generated name:** `custom`
- **Generated description:** `A custom`
- **Generation result:** ⚠️ SUCCESS (but misrouted to fallback)
- **Model type:** `box` (fallback because category = custom)
- **Parameters:** `{'width': 50, 'height': 30.0, 'depth': 40.0}`
- **Output:** `from_description.stl` (50.0 × 40.0 × 30.0 mm) — a generic box, not a puzzle piece

---

## Part 3 — Honest Capability Report

### 3.1 Which of the 10 requests actually worked?

**Only 1 request produced a sensible, correctly-categorized model:**

| Test | Input | Category | Model Type | Verdict |
|------|-------|----------|------------|---------|
| 1 | "I need a small box to store screws, about 80mm wide" | `box` | `box` | ✅ **Correct** — user asked for a box, got a box with the right width |

**The other 9 all fell back to a generic shape that does not match the user's intent:**

- **Tests 2, 4, 6, 7, 10** → `custom` → generic `box` fallback (50×40×30 mm or dimension-scaled box)
- **Test 3** → `bracket` → L-bracket (not a phone stand)
- **Test 5** → `hook` → wall hook (not a cable clip)
- **Test 8** → `hook` → wall hook (not a name tag holder)
- **Test 9** → `bracket` → L-bracket (closest available, but still not a router wall mount)

### 3.2 Which ones failed, misrouted, or fell back? Why?

| Test | Input | Detected | Why it failed |
|------|-------|----------|---------------|
| 2 | cup holder | `custom` | No keyword match: "cup", "holder", "vent" are absent from `CATEGORY_KEYWORDS`. |
| 3 | phone stand | `bracket` | "stand" is in `BRACKET` keywords. The parser cannot distinguish a "phone stand" from a "monitor stand" or "shelf bracket". No phone-specific keywords exist. |
| 4 | keychain | `custom` | "keychain", "key", "ring" (in this context) are absent from all keyword lists. |
| 5 | cable clip | `hook` | "clip" is in `HOOK` keywords. The parser treats "cable clip" the same as "wall hook". No cable-specific keywords exist. |
| 6 | gear | `custom` | "gear", "teeth" are absent from all keyword lists. |
| 7 | vase | `custom` | "vase" is absent from all keyword lists. |
| 8 | name tag holder | `hook` | "clip" matched `HOOK`. "name tag", "holder" (as a badge accessory) are absent. |
| 9 | wall mount for router | `bracket` | "wall mount" is in `BRACKET` keywords. This is the *closest* match, but the generator produces a generic L-bracket, not a router-specific mount. |
| 10 | puzzle piece | `custom` | "puzzle" is absent from all keyword lists. |

### 3.3 Which categories handle real variety, and which only work with exact phrases?

#### Categories that genuinely handle some variety:
- **`box`** — The keyword is just `"box"`, which is common and unambiguous. Works for most box-like requests.
- **`bracket`** — Catches "wall mount", "bracket", "stand", "mount", "brace". Reasonably broad, but **over-catches** (e.g., "phone stand" is not a bracket).
- **`hook`** — Catches "hook", "clip", "clamp", "hanger", "grip", "grabber". Broad, but **over-catches** (e.g., "cable clip" is not a wall hook).

#### Categories that only work with very specific phrasing:
- **`tube_squeezer`** — Requires words like "tube squeezer", "toothpaste", "lotion", "dispenser", "roller". A user saying "I need something to squeeze my lotion tube" would likely work, but "tube press" or "paste extractor" would not.
- **`enclosure`** — Requires "electronics box", "project box", "raspberry pi", "arduino", "enclosure", "housing", "case", "hollow", "lid", etc. Works for electronics projects but misses generic "container with lid" phrasing.
- **`cylinder`** — Requires "cylinder", "rod", "peg", "disc", "pin", "shaft", "round", "tube". Reasonably broad for round objects.
- **`spacer`** — Requires "spacer", "standoff", "washer", "bushing", "grommet", "pcb". Very niche; only works for mechanical/electronics contexts.

#### The fundamental problem:
The keyword system is **binary presence/absence** with no semantic understanding. There is no concept of:
- Synonyms ("cup holder" ≠ "container")
- Negative context ("phone stand" is not a "monitor stand")
- Functional description ("holds my phone at an angle" does not map to any category)
- Shape description ("puzzle piece", "gear", "vase" have no generators)

### 3.4 Categories/shapes the system has zero chance of handling today

Based on the actual `SUPPORTED_TYPES` set in `cad_generator.py` (line 75–83) and the `CATEGORY_KEYWORDS` dictionary, the following common user requests **cannot** be correctly handled:

| Request Type | Why it's impossible today |
|--------------|---------------------------|
| **Gear** | No `gear` category, no generator, no keywords. |
| **Vase** | No `vase` category, no generator, no keywords. |
| **Puzzle piece** | No `puzzle` category, no generator, no keywords. |
| **Cup holder** | No `cup_holder` category, no generator, no keywords. |
| **Keychain** | No `keychain` category, no generator, no keywords. |
| **Phone stand** | No `phone_stand` category; misrouted to `bracket`. |
| **Cable clip / cable organizer** | No `cable_clip` category; misrouted to `hook`. |
| **Name tag / badge holder** | No `badge_holder` category; misrouted to `hook`. |
| **Any organic/curved shape** | All generators produce rectilinear or simple revolved shapes (boxes, cylinders, L-brackets, hooks). No splines, lofts, or freeform surfaces. |
| **Any multi-part assembly** | Every generator produces a single solid. No snap-fit joints, hinges, threads, or interlocking parts. |
| **Any shape requiring holes in specific places** | Generators have fixed hole patterns (e.g., bracket has two holes at fixed positions). User cannot request "a hole in the center" or "two holes 20mm apart". |

### Summary

The system today is a **7-shape parametric generator** with a **keyword-based router** that:
1. **Works well** when the user explicitly names one of the 7 supported shapes (box, cylinder, tube squeezer, bracket, enclosure, spacer, hook).
2. **Fails silently** for everything else by producing a generic box.
3. **Over-catches** broad terms like "stand", "mount", "clip" into categories that may not match the user's intent.
4. **Has no semantic understanding** — it cannot infer shape from function, only from keyword presence.

The gap between what a user might reasonably ask for and what the system can actually generate is **very large**.
