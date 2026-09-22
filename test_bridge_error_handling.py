"""Error-handling tests for the Python→PrusaMCP bridge."""
import subprocess
import json
from pathlib import Path


def run_bridge(stl_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node",
         "C:/Users/K1 Center/Downloads/test/PrusaMCP/cli-analyze.js",
         stl_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


# Test 1: Valid file — confirm 12.5% overhang, thin walls false
r1 = run_bridge("C:/Users/K1 Center/Desktop/vibe-print/phone_stand.stl")
print("=== Test 1: Valid file ===")
print(f"  Return code:    {r1.returncode}")
parsed = json.loads(r1.stdout)
print(f"  overhangPercent: {parsed['overhangPercent']}%")
print(f"  hasThinWalls:    {parsed['hasThinWalls']}")

# Test 2: Non-existent file
r2 = run_bridge("C:/nonexistent/file.stl")
print("\n=== Test 2: Non-existent file ===")
print(f"  Return code:    {r2.returncode}  (expected: non-zero)")
print(f"  stderr:         {r2.stderr.strip()}")

# Test 3: No argument
r3 = subprocess.run(
    ["node", "C:/Users/K1 Center/Downloads/test/PrusaMCP/cli-analyze.js"],
    capture_output=True, text=True, encoding="utf-8", timeout=30,
)
print("\n=== Test 3: No argument ===")
print(f"  Return code:    {r3.returncode}  (expected: non-zero)")
print(f"  stderr:         {r3.stderr.strip()}")