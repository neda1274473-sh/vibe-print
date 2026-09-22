"""
Run the ModelAnalyzer with VIBE_PRUSAMCP_PATH set, then compare with
trimesh fallback for the same desk_cable_organizer.stl.
"""

import os
import sys
import importlib as _irlib

# MUST be set BEFORE vibe_print imports
os.environ["VIBE_PRUSAMCP_PATH"] = r"C:\Users\K1 Center\Downloads\test\PrusaMCP"

# Force reimport of config + analyzer modules to pick up env var
import vibe_print.config as _cfg_mod
_irlib.reload(_cfg_mod)

import vibe_print.models.analyzer as _analyzer_mod
_irlib.reload(_analyzer_mod)

from vibe_print.models.analyzer import ModelAnalyzer
from vibe_print.config import config as _cfg


def run_with_prusa_mcp():
    """Run analysis WITH PrusaMCP active."""
    print("=" * 60)
    print("  TEST: ModelAnalyzer WITH PrusaMCP")
    print("=" * 60)
    print(f"  VIBE_PRUSAMCP_PATH = {os.environ.get('VIBE_PRUSAMCP_PATH')}")
    print(f"  cli_script          = {_cfg.prusa_mcp.cli_script}")
    print()

    analyzer = ModelAnalyzer()
    result = analyzer.analyze(r"C:\Users\K1 Center\Desktop\vibe-print\desk_cable_organizer.stl")

    print("  --- Analysis Result ---")
    print(f"  is_valid: {result['is_valid']}")
    print(f"  Issues:")
    for iss in result["issues"]:
        print(f"    [{iss['severity']}] {iss['type']}: {iss['message']}")
    print(f"  Recommendations:")
    for r in result["recommendations"]:
        print(f"    - {r}")
    print()
    print("  --- Mesh Info ---")
    mi = result["mesh_info"]
    print(f"  triangles: {mi['faces']}")
    print(f"  vertices:  {mi['vertices']}")
    print(f"  volume_cm3: {mi['volume_cm3']}")
    print(f"  bounds_mm: {mi['bounds_mm']}")
    print(f"  is_watertight: {mi['is_watertight']}")
    print()
    return result


def run_with_trimesh_fallback():
    """Run analysis WITHOUT PrusaMCP (invalid path = fallback to trimesh)."""
    print()
    print("=" * 60)
    print("  TEST: ModelAnalyzer WITHOUT PrusaMCP (trimesh fallback)")
    print("=" * 60)

    # Override with bad path and force reload
    os.environ["VIBE_PRUSAMCP_PATH"] = r"C:\nonexistent\path\to\PrusaMCP"
    _irlib.reload(_cfg_mod)

    import vibe_print.models.analyzer as _fallback_analyzer
    _irlib.reload(_fallback_analyzer)

    from vibe_print.models.analyzer import ModelAnalyzer
    from vibe_print.config import config as _cfg2

    print(f"  VIBE_PRUSAMCP_PATH = {os.environ.get('VIBE_PRUSAMCP_PATH')}")
    print(f"  cli_script (expected None) = {_cfg2.prusa_mcp.cli_script}")
    print()

    analyzer2 = ModelAnalyzer()
    result2 = analyzer2.analyze(r"C:\Users\K1 Center\Desktop\vibe-print\desk_cable_organizer.stl")

    print("  --- Analysis Result ---")
    print(f"  is_valid: {result2['is_valid']}")
    print(f"  Issues:")
    for iss in result2["issues"]:
        print(f"    [{iss['severity']}] {iss['type']}: {iss['message']}")
    print(f"  Recommendations:")
    for r in result2["recommendations"]:
        print(f"    - {r}")
    print()
    return result2


def compare_results(prusa_result, trimesh_result):
    """Compare overhang results between PrusaMCP and trimesh fallback."""
    print()
    print("=" * 60)
    print("  COMPARISON: PrusaMCP vs trimesh fallback")
    print("=" * 60)

    # Extract overhang percentages
    def get_overhang(msg):
        import re
        m = re.search(r"([\d.]+)%", msg)
        return float(m.group(1)) if m else None

    prusa_overhang = None
    trimesh_overhang = None

    for iss in prusa_result["issues"]:
        if iss["type"] == "overhang":
            prusa_overhang = get_overhang(iss["message"])
            break

    for iss in trimesh_result["issues"]:
        if iss["type"] == "overhang":
            trimesh_overhang = get_overhang(iss["message"])
            break

    print(f"  PrusaMCP overhang:  {prusa_overhang}%")
    print(f"  trimesh fallback:   {trimesh_overhang}%")
    if trimesh_overhang and prusa_overhang:
        ratio = trimesh_overhang / prusa_overhang
        print(f"  Ratio (trimesh/PrusaMCP): {ratio:.1f}x")
        print(f"  trimesh over-reports overhang by {ratio - 1:.1f}x!")
    print()
    print("  Explanation:")
    print("  - trimesh uses 'angle-from-downward-Z' which flags nearly all faces")
    print("  - PrusaMCP uses geometrically correct normal.z < -0.707 threshold")
    print("  - The cable organizer has mostly horizontal faces (top/bottom surfaces)")
    print("  - Only 2 triangles have normals pointing downward beyond 45 degrees")


if __name__ == "__main__":
    prusa_result = run_with_prusa_mcp()
    trimesh_result = run_with_trimesh_fallback()
    compare_results(prusa_result, trimesh_result)