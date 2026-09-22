"""
test_prusa_mcp_bridge.py
=======================
Proof-of-concept: call PrusaMCP's cli-analyze.js from Python and receive
its JSON output as a native Python dict.

This is a standalone test script — NOT integrated into analyzer.py.
"""
import subprocess
import json
import sys
from pathlib import Path


def analyze_with_prusa_mcp(stl_path: str) -> dict:
    """
    Bridge: invoke PrusaMCP's cli-analyze.js as a subprocess and parse its JSON.

    Args:
        stl_path: Absolute path to the STL file.

    Returns:
        Parsed Python dict matching PrusaMCP's analyzeMesh() output schema.
    """
    prusa_mcp_root = Path(r"C:\Users\K1 Center\Downloads\test\PrusaMCP")
    cli_script = prusa_mcp_root / "cli-analyze.js"

    result = subprocess.run(
        ["node", str(cli_script), str(Path(stl_path).absolute())],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"PrusaMCP CLI exited with code {result.returncode}\n"
            f"stderr: {result.stderr}"
        )

    # stdout is the raw JSON — parse it
    return json.loads(result.stdout)


def main():
    phone_stand = Path(r"C:\Users\K1 Center\Desktop\vibe-print\phone_stand.stl")
    print(f"STL: {phone_stand}")
    print(f"Exists: {phone_stand.exists()}\n")

    print("Calling PrusaMCP via subprocess ...")
    analysis = analyze_with_prusa_mcp(str(phone_stand))

    print("Received Python dict from PrusaMCP:\n")
    print(json.dumps(analysis, indent=2))

    print("\n--- Key fields ---")
    print(f"  triangleCount      : {analysis['triangleCount']}")
    print(f"  volume             : {analysis['volume']:.2f} mm³")
    print(f"  surfaceArea        : {analysis['surfaceArea']:.2f} mm²")
    print(f"  boundingBox (min)  : {analysis['boundingBox']['min']}")
    print(f"  boundingBox (max)  : {analysis['boundingBox']['max']}")
    print(f"  isManifold         : {analysis['isManifold']}")
    print(f"  nonManifoldEdges   : {analysis['nonManifoldEdges']}")
    print(f"  overhangPercent    : {analysis['overhangPercent']}%")
    print(f"  overhangTriangles  : {analysis['overhangTriangles']}")
    print(f"  hasThinWalls       : {analysis['hasThinWalls']}")
    print(f"  thinWallPercent    : {analysis['thinWallPercent']}%")
    print(f"  hasSmallDetails    : {analysis['hasSmallDetails']}")
    print(f"  smallDetailPercent : {analysis['smallDetailPercent']}%")


if __name__ == "__main__":
    main()