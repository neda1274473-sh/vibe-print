#!/usr/bin/env python
"""Write updated integration test file for Step 1d."""

content = r'''"""test_analyzer_prusa_mcp_integration.py - Step 1d verification."""
import os as _os

_os.environ["VIBE_PRUSAMCP_PATH"] = r"C:\Users\K1 Center\Downloads\test\PrusaMCP"
from vibe_print.models.analyzer import ModelAnalyzer

# Test 1: PrusaMCP available - thin-wall check via PrusaMCP
# PrusaMCP confirmed: hasThinWalls=False, thinWallPercent=0.0%
# Overhang: 0.877% (2/228 triangles) - below 10% threshold, no issue raised
print("=== Test 1: PrusaMCP available ===")
analyzer = ModelAnalyzer()
result = analyzer.analyze(r"C:\Users\K1 Center\Desktop\vibe-print\phone_stand.stl")
print(f"  faces={result['mesh_info']['faces']}, watertight={result['mesh_info']['is_watertight']}")
print(f"  Issues ({len(result['issues'])}):")
for iss in result["issues"]:
    print(f"    [{iss['severity']}] {iss['type']}: {iss['message']}")

# Verify: hasThinWalls=False in PrusaMCP -> NO thin_walls issue should appear
thin_issues = [i for i in result["issues"] if i["type"] == "thin_walls"]
assert len(thin_issues) == 0, f"Expected no thin_walls issue (hasThinWalls=False), got: {thin_issues}"
print("  PASS: No thin_walls issue (PrusaMCP hasThinWalls=False)")

# Verify: overhang is 0.9% - below 10% threshold, no overhang issue raised
overhang_issues = [i for i in result["issues"] if i["type"] == "overhang"]
assert len(overhang_issues) == 0, "Expected no overhang issue (0.9% < 10% threshold)"
print("  PASS: No overhang issue (0.9% < 10% threshold)")

# Verify: is_valid=True (no issues at all)
assert result["is_valid"] is True, f"Expected is_valid=True, got {result['is_valid']}"
print("  PASS: model is valid (no issues)")

# Test 2: Invalid path - graceful fallback, no crash
print()
print("=== Test 2: Invalid path - fallback ===")
_os.environ["VIBE_PRUSAMCP_PATH"] = r"C:\nonexistent\path\to\PrusaMCP"

import importlib as _irlib
from vibe_print import config as _cfg_mod
_irlib.reload(_cfg_mod)

import vibe_print.models.analyzer as _analyzer_mod
_irlib.reload(_analyzer_mod)

from vibe_print.config import config as _cfg
from vibe_print.models.analyzer import ModelAnalyzer

print(f"  cli_script (expected None): {_cfg.prusa_mcp.cli_script}")
assert _cfg.prusa_mcp.cli_script is None, f"Expected cli_script=None, got {_cfg.prusa_mcp.cli_script}"

analyzer2 = ModelAnalyzer()
result2 = analyzer2.analyze(r"C:\Users\K1 Center\Desktop\vibe-print\phone_stand.stl")
print(f"  Issues ({len(result2['issues'])}):")
for iss in result2["issues"]:
    print(f"    [{iss['severity']}] {iss['type']}: {iss['message']}")

# Verify: fallback uses trimesh - should show thin_walls issue (old heuristic)
thin_issues_fb = [i for i in result2["issues"] if i["type"] == "thin_walls"]
assert len(thin_issues_fb) > 0, f"Expected thin_walls issue in fallback (trimesh), got: {thin_issues_fb}"
print("  PASS: Fallback correctly shows thin_walls issue (trimesh heuristic)")
print("  PASS: No crash with invalid path - fallback used")
print()
print("ALL TESTS PASSED")
'''

with open(r"c:\Users\K1 Center\Desktop\vibe-print\test_analyzer_prusa_mcp_integration.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Written successfully")