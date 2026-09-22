import os, sys

# Write the integration test file
content = r'''"""
test_analyzer_prusa_mcp_integration.py
======================================
CRITICAL: VIBE_PRUSAMCP_PATH must be set BEFORE vibe_print imports.
"""
import os as _os
import re as _re
import sys

# MUST be first — before any vibe_print import
_os.environ["VIBE_PRUSAMCP_PATH"] = r"C:\Users\K1 Center\Downloads\test\PrusaMCP"

from vibe_print.models.analyzer import ModelAnalyzer  # noqa: E402

def _extract_pct(msg):
    m = _re.search(r"([\d.]+)%", msg)
    return float(m.group(1)) if m else None

# ── Test 1: PrusaMCP available — expect 12.5% ────────────────────────────
print("=== Test 1: PrusaMCP available ===")
analyzer = ModelAnalyzer()
result = analyzer.analyze(r"C:\Users\K1 Center\Desktop\vibe-print\phone_stand.stl")
print(f"  faces={result["mesh_info"]["faces"]}, watertight={result["mesh_info"]["is_watertight"]}")
print(f"  Issues ({len(result["issues"])}):")
for iss in result["issues"]:
    print(f"    [{iss["severity"]}] {iss["type"]}: {iss["message"]}")

overhang_pct = None
for iss in result["issues"]:
    if iss["type"] == "overhang":
        overhang_pct = _extract_pct(iss["message"])
        break

print(f"  Overhang %: {overhang_pct}")
assert overhang_pct is not None, "No overhang issue found"
assert abs(overhang_pct - 12.5) < 0.1, f"Expected ~12.5%, got {overhang_pct}%"
print("  PASS: Got 12.5% (was 87.5% before fix)")

# ── Test 2: Invalid path — graceful fallback, no crash ──────────────────
print()
print("=== Test 2: Invalid path — fallback ===")
_os.environ["VIBE_PRUSAMCP_PATH"] = r"C:\nonexistent\path\to\PrusaMCP"
import importlib as _irlib
from vibe_print import config as _cfg_mod
_irlib.reload(_cfg_mod)
from vibe_print.config import config as _cfg
print(f"  cli_script (expected None): {_cfg.prusa_mcp.cli_script}")
assert _cfg.prusa_mcp.cli_script is None

analyzer2 = ModelAnalyzer()
result2 = analyzer2.analyze(r"C:\Users\K1 Center\Desktop\vibe-print\phone_stand.stl")
print(f"  Issues ({len(result2["issues"])}):")
for iss in result2["issues"]:
    print(f"    [{iss["severity"]}] {iss["type"]}: {iss["message"]}")
print(f"  is_valid={result2["is_valid"]}")
print("  PASS: No crash with invalid path")
print()
print("ALL TESTS PASSED")
'''

with open(r"C:\Users\K1 Center\Desktop\vibe-print\test_analyzer_prusa_mcp_integration.py", "w", encoding="utf-8") as f:
    f.write(content)
print("File written.")