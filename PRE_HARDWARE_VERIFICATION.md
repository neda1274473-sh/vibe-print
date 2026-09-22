# Pre-Hardware Verification Report

**Date:** 2026-08-20
**Test method:** Real code execution via `run_verification.py` — no mocks for parsing, generation, analysis, or validation. Slicer runs in MOCK mode (no real PrusaSlicer/BambuStudio installed).
**Environment:** Windows 10, Python with CadQuery 2.x available, trimesh fallback not used.

---

## Request 1: Toothpaste Tube Squeezer (40mm)

**Input text:** `"I need a squeezer for a 40mm diameter tube of toothpaste"`

### Parsed Requirements
| Field | Value |
|-------|-------|
| Category | `tube_squeezer` |
| Detected dimensions | `[{value: 40.0, unit: "mm", context: "diameter", mm: 40.0}]` |
| Primary dimension | **40.0 mm** |
| Wall thickness | 2.0 mm |
| Needs strength | false |
| Fit type | sliding |
| Reference object | `"I need a squeezer for a 40mm diameter tube"` (noisy but harmless) |

**Human-match check:** ✅ **Correct.** The parser correctly identified `tube_squeezer` and extracted exactly `40mm` with context `diameter`. This matches what a human would expect.

### Generated Model
| Property | Value |
|----------|-------|
| File path | `C:\Users\K1CENT~1\AppData\Local\Temp\vibe-print\generated\from_description.stl` |
| File size | **70,284 bytes** (~70 KB) |
| Model type | `tube_squeezer` |
| Parameters used | `tube_diameter: 40.0`, `wall_thickness: 2.0`, `width: 60.0` |
| Generation engine | CadQuery (real parametric CAD) |

### Model Analysis (real `analyze_model` run)
| Property | Value |
|----------|-------|
| Vertices | 784 |
| Faces | 1,564 |
| Volume | **26.25 cm³** |
| Surface area | 106.47 cm² |
| Bounding box | 60.0 × 30.0 × 44.0 mm |
| **Watertight** | **true** |
| Winding consistent | true |

### Validation Result
- **Pass/fail:** ✅ **PASS** (no blocking issues)
- Non-blocking warnings: 76.1% overhang (supports recommended), 1,224 thin-wall edges

### Slicing Result
- **Mode:** MOCK (honest — no real slicer installed)
- Estimated time: **7.5 minutes**
- Estimated filament: **2.1 g**
- Layer count: 77

### Recovery Actions
- **None triggered.**

---

## Request 2: Mounting Bracket (60mm tall, two screw holes)

**Input text:** `"Can you make a mounting bracket with two screw holes, about 60mm tall?"`

### Parsed Requirements
| Field | Value |
|-------|-------|
| Category | `bracket` |
| Detected dimensions | `[{value: 60.0, unit: "mm", context: "tall", mm: 60.0}]` |
| Primary dimension | **60.0 mm** |
| Wall thickness | 2.5 mm (auto-bumped because dim > 50 mm) |
| Needs strength | false |
| Fit type | sliding |

**Human-match check:** ✅ **Correct.** Category `bracket` is right, and `60mm` was extracted with context `tall`. The "two screw holes" detail is **not captured** in the parameters — the generator always uses a fixed `hole_diameter: 5.0` and places two holes regardless, so the output happens to match the request by coincidence, not by understanding.

### Generated Model
| Property | Value |
|----------|-------|
| File path | `...\from_description.stl` |
| File size | **10,284 bytes** (~10 KB) |
| Model type | `bracket` |
| Parameters used | `width: 60.0`, `height: 48.0`, `thickness: 2.5`, `hole_diameter: 5.0` |
| Generation engine | CadQuery |

### Model Analysis
| Property | Value |
|----------|-------|
| Vertices | 100 |
| Faces | 200 |
| Volume | **11.28 cm³** |
| Surface area | 97.52 cm² |
| Bounding box | 60.0 × 30.05 × 48.0 mm |
| **Watertight** | **true** |

### Validation Result
- **Pass/fail:** ✅ **PASS**
- Non-blocking warnings: 78.0% overhang, 134 thin-wall edges

### Slicing Result
- **Mode:** MOCK
- Estimated time: **2.0 minutes**
- Estimated filament: **0.6 g**
- Layer count: 50

### Recovery Actions
- **None triggered.**

---

## Request 3: Small Open Box (50×30×20mm)

**Input text:** `"I want a small open box, 50x30x20mm, to organize screws on my desk"`

### Parsed Requirements
| Field | Value |
|-------|-------|
| Category | `box` |
| Detected dimensions | `[{value: 20.0, unit: "mm", context: "", mm: 20.0}]` |
| Primary dimension | **20.0 mm** |
| Wall thickness | 2.0 mm |
| Needs strength | false |
| Fit type | sliding |

**Human-match check:** ❌ **WRONG.** A human reading "50x30x20mm" would expect three dimensions: width=50, depth=30, height=20. The parser only extracted the **last** number (`20`) with **no context**, and the generator then produced a box of 20 × 12 × 16 mm. The requested 50×30×20mm was completely lost.

### Generated Model
| Property | Value |
|----------|-------|
| File path | `...\from_description.stl` |
| File size | **684 bytes** (~0.7 KB) |
| Model type | `box` |
| Parameters used | `width: 20.0`, `height: 12.0`, `depth: 16.0` |
| Generation engine | CadQuery |

### Model Analysis
| Property | Value |
|----------|-------|
| Vertices | 8 |
| Faces | 12 |
| Volume | **3.84 cm³** |
| Surface area | 15.04 cm² |
| Bounding box | 20.0 × 16.0 × 12.0 mm |
| **Watertight** | **true** |

### Validation Result
- **Pass/fail:** ✅ **PASS** (technically passes watertight/volume checks)
- Non-blocking warning: 83.3% overhang

### Slicing Result
- **Mode:** MOCK
- Estimated time: **2.0 minutes**
- Estimated filament: **0.6 g**
- Layer count: 50

### Recovery Actions
- **None triggered.** (The system had no way to know the dimensions were