# Pre-Hardware Verification Report — Part 2 of 3

**Date:** 2026-08-20
**Test method:** Real code execution via `run_part2.py` — no mocks for parsing, generation, analysis, or validation. Slicer runs in MOCK mode (no real PrusaSlicer/BambuStudio installed).
**Environment:** Windows 10, Python with CadQuery 2.x available, trimesh fallback not used.
**Requests tested:** 2 of 6 (Part 2 — requests 3 and 4)

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
| Reference object | `""` |
| Extracted numbers | `[50.0, 30.0, 20.0]` |

**Human-match check:** ❌ **WRONG.** A human reading "50x30x20mm" would expect three dimensions: width=50, depth=30, height=20. The parser extracted all three numbers (`[50.0, 30.0, 20.0]`) but only the **last** number (`20.0`) was promoted to a target dimension with **no context**. The generator then produced a box of 20 × 16 × 12 mm. The requested 50×30×20mm was completely lost.

### Generated Model
| Property | Value |
|----------|-------|
| File path | `C:\Users\K1CENT~1\AppData\Local\Temp\vibe-print\generated\from_description.stl` |
| File size | **684 bytes** (~0.7 KB) |
| Model type | `box` |
| Parameters used | `width: 20.0`, `height: 12.0`, `depth: 16.0` |
| Generation engine | CadQuery |

### Model Analysis (real `analyze_model` run)
| Property | Value |
|----------|-------|
| Vertices | 8 |
| Faces | 12 |
| Volume | **3.84 cm³** |
| Surface area | 15.04 cm² |
| Bounding box | 20.0 × 16.0 × 12.0 mm |
| **Watertight** | **true** |
| Winding consistent | true |

### Validation Result
- **Pass/fail:** ✅ **PASS** (technically passes watertight/volume checks)
- Non-blocking warning: 83.3% overhang

### Slicing Result
- **Mode:** MOCK (honest — no real slicer installed)
- Estimated time: **2.0 minutes**
- Estimated filament: **0.6 g**
- Layer count: 50

### Recovery Actions
- **None triggered.** (The system had no way to know the dimensions were wrong.)

---

## Request 4: Coat Hook (Wall-Mounted)

**Input text:** `"A hook that can hold a coat, mounted on a wall"`

### Parsed Requirements
| Field | Value |
|-------|-------|
| Category | `hook` |
| Detected dimensions | `[]` (none) |
| Primary dimension | **None** |
| Wall thickness | 2.0 mm |
| Needs strength | false |
| Fit type | sliding |
| Reference object | `"A hook that can"` (noisy/truncated) |
| Extracted numbers | `[]` |

**Human-match check:** ⚠️ **PARTIAL.** Category `hook` is correct. No dimensions were provided in the input, so the empty dimensions list is expected. The reference object is noisy (`"A hook that can"` instead of the full phrase), but this is harmless.

### Generated Model
| Property | Value |
|----------|-------|
| File path | `C:\Users\K1CENT~1\AppData\Local\Temp\vibe-print\generated\from_description.stl` |
| File size | **10,484 bytes** (~10 KB) |
| Model type | `hook` |
| Parameters used | `arm_length: 40.0` (default) |
| Generation engine | CadQuery |

### Model Analysis (real `analyze_model` run)
| Property | Value |
|----------|-------|
| Vertices | 108 |
| Faces | 208 |
| Volume | **0.23 cm³** |
| Surface area | 4.66 cm² |
| Bounding box | 46.0 × 4.0 × 8.0 mm |
| **Watertight** | **true** |
| Winding consistent | true |

### Validation Result
- **Pass/fail:** ✅ **PASS**
- Non-blocking warnings: 90.4% overhang, 127 thin-wall edges

### Slicing Result
- **Mode:** MOCK
- Estimated time: **2.0 minutes**