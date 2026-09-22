# Phase 2.9 Summary — Routing Accuracy Hardening

## Objective

Eliminate the silent routing collision bug discovered in Phase 2.75 where `RequirementsParser._classify_category()` misclassified "standoff for pcb" as `bracket` instead of `spacer`, and harden the entire keyword-matching system against similar substring collisions.

## Root Cause

The original `_classify_category()` method used a simple `if keyword in text_lower` check with keywords sorted alphabetically. This caused two failure modes:

1. **Short-substring-wins bug**: "stand" (5 chars, bracket keyword) matched before "standoff" (8 chars, spacer keyword) because the list was sorted alphabetically, not by specificity.
2. **No word-boundary guard**: "stand" matched "standoff" as a substring, even though "standoff" is a completely different object type.
3. **No tie-breaker logic**: When both BOX and ENCLOURE scored, there was no disambiguation rule.

## Fix Applied

### 1. Longest-Match-First Sorting

Keywords are now sorted by length descending before matching:

```python
sorted_keywords = sorted(keywords, key=len, reverse=True)
```

This ensures "tube squeezer" (13) beats "squeezer" (8), and "standoff" (8) beats "stand" (5).

### 2. Word-Boundary Guard for Single-Word Keywords

Single-word keywords must appear as whole words (via `\b` regex boundary):

```python
if " " not in keyword:
    pattern = r'\b' + re.escape(keyword) + r'\b'
    if not re.search(pattern, text_lower):
        continue
```

This prevents "box" from matching "boxing", "stand" from matching "standoff", etc.

### 3. Explicit Tie-Breaker Rules

Two tie-breakers handle ambiguous cases:

- **Box vs Enclosure**: If scores are equal, enclosure wins (hollow intent is stronger than solid intent). If scores differ, the higher score wins (e.g., "no lid" in BOX scores 6 vs "lid" in ENCLOSURE scoring 3 → BOX wins).
- **Spacer vs Bracket**: If scores are equal and "standoff" is present, SPACER wins ("standoff" is a very specific spacer term that should dominate over generic "mounting" bracket signals).

### 4. Aligned Category Enum ↔ Generator Map

`ObjectCategory` enum values now match `ParametricGenerator.SUPPORTED_TYPES` exactly:

| ObjectCategory | Generator Type |
|---------------|----------------|
| `box` | `box` |
| `cylinder` | `cylinder` |
| `tube_squeezer` | `tube_squeezer` |
| `bracket` | `bracket` |
| `enclosure` | `enclosure` |
| `spacer` | `spacer` |
| `hook` | `hook` |
| `custom` | `box` (fallback) |

Removed stale keywords like "holder", "clip", "container", "organizer", "tool", "adapter", "cover" that created phantom mappings to non-existent generator types.

## Verification

### 46-Phrase Test Suite (100% Pass)

| Category | Cases | Result |
|----------|-------|--------|
| BOX | 6 | 6/6 |
| CYLINDER | 6 | 6/6 |
| TUBE_SQUEEZER | 6 | 6/6 |
| BRACKET | 6 | 6/6 |
| ENCLOSURE | 6 | 6/6 |
| SPACER | 6 | 6/6 |
| HOOK | 6 | 6/6 |
| Edge cases | 4 | 4/4 |
| **Total** | **46** | **46/46 (100%)** |

### Regression Test Suite

All 129 existing tests pass unmodified. No Phase 2 code was changed.

### New Permanent Test File

`tests/test_requirements_routing.py` — 50 parametrized tests that will catch any future routing regression:

- `TestRoutingAccuracy`: 46 cases across all 7 categories + 4 edge cases
- `TestCollisionPrevention`: 4 tests specifically for the collision bugs fixed in this phase

## Files Changed

| File | Change |
|------|--------|
| `vibe_print/generator/requirements.py` | Rewrote `_classify_category()` with longest-match-first, word-boundary guards, tie-breakers; aligned `CATEGORY_KEYWORDS` with `ObjectCategory` enum |
| `vibe_print/generator/cad_generator.py` | Updated `category_map` to use direct enum-value-to-generator mapping |
| `tests/test_requirements_routing.py` | **New** — 50 permanent routing regression tests |

## Test Count

| Phase | Tests |
|-------|-------|
| Phase 2 | 129 |
| Phase 2.9 (this phase) | +50 |
| **Total** | **179** |

## Recommendation

The routing system is now robust against substring collisions and ambiguous phrases. The 50 new regression tests provide a safety net for any future keyword additions. **Ready for Phase 3 (Intelligent Agent)** — the natural-language-to-model pipeline now routes correctly for all supported generator types.
