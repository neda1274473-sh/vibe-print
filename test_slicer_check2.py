import sys, os, asyncio, pathlib
sys.path.insert(0, ".")

from vibe_print.slicer.cli import SlicerCLI, MockSlicerCLI, get_slicer_cli
from vibe_print.config import config
from pathlib import Path

# 1. Check configuration
print("=== CONFIGURATION ===")
env_path = os.environ.get("VIBE_SLICER_PATH", "<not set>")
print(f"VIBE_SLICER_PATH env var: {env_path}")
print(f"config.slicer.executable_path: {config.slicer.executable_path}")
print(f"config.slicer.executable_path exists: {config.slicer.executable_path.exists()}")

# 2. Check via factory
print()
print("=== FACTORY (get_slicer_cli) ===")
cli = get_slicer_cli()
print(f"Type returned: {type(cli).__name__}")
avail, msg = cli.is_available()
print(f"is_available: {avail} | msg: {msg}")
print(f"Is MockSlicerCLI: {isinstance(cli, MockSlicerCLI)}")

# 3. ACTUALLY slice phone_stand.stl
print()
print("=== ACTUAL SLICE of phone_stand.stl ===")
model_path = Path("C:/Users/K1 Center/Desktop/vibe-print/phone_stand.stl")
print(f"Model exists: {model_path.exists()}")
print(f"Model size: {model_path.stat().st_size} bytes")

result = asyncio.run(cli.slice_model(model_path))
result_dict = result.to_dict()
result_dict["mode"] = "MOCK" if isinstance(cli, MockSlicerCLI) else "REAL"

print(f"\nSliceResult:")
for k, v in result_dict.items():
    print(f"  {k}: {v}")

# 4. Check the produced gcode file
print()
print("=== PRODUCED GCODE FILE ===")
gcode_path = result_dict.get("output_gcode")
if gcode_path:
    gp = Path(gcode_path)
    print(f"G-code path: {gcode_path}")
    print(f"G-code exists: {gp.exists()}")
    print(f"G-code size: {gp.stat().st_size} bytes")
    content = gp.read_text()
    print(f"G-code content:\n{content}")
else:
    print("No G-code file produced")

# 5. Check the 3mf file
print()
print("=== PRODUCED 3MF FILE ===")
mf_path = result_dict.get("output_3mf")
if mf_path:
    mp = Path(mf_path)
    print(f"3MF path: {mf_path}")
    print(f"3MF exists: {mp.exists()}")
    print(f"3MF size: {mp.stat().st_size} bytes")
    print(f"3MF first 10 bytes (hex): {mp.read_bytes()[:10].hex()}")
else:
    print("No 3MF file produced")

# 6. Check cli_output field
print()
print("=== CLI OUTPUT FIELD ===")
print(repr(result.cli_output))