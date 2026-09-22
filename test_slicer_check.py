import sys, os, asyncio, pathlib
sys.path.insert(0, ".")

from vibe_print.slicer.cli import SlicerCLI, MockSlicerCLI, get_slicer_cli
from vibe_print.config import config
from pathlib import Path

# 1. Check configuration
print("=== CONFIGURATION ===")
env_path = os.environ.get("VIBE_SLICER_PATH", "<not set>")
print(f"VIBE_OLICER_PATH env var: {env_path}")
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

# 3. Check existing gcode files
print()
print("=== EXISTING G-CODE FILES ===")
temp_dir = config.slicer.temp_dir
sliced_dir = temp_dir / "sliced"
print(f"temp_dir from config: {temp_dir}")
print(f"Sliced dir: {sliced_dir}")
print(f"Sliced dir exists: {sliced_dir.exists()}")
if sliced_dir.exists():
    gcode_files = list(sliced_dir.glob("*.gcode"))
    print(f"G-code files found: {len(gcode_files)}")
    for f in gcode_files[:10]:
        content = f.read_text()
        first_lines = "\n".join(content.split("\n")[:3])
        print(f"  {f.name} | size={f.stat().st_size} bytes | first 3 lines:\n{first_lines}\n")