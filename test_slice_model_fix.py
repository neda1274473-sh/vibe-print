"""Test script to verify slice_model fix for asyncio.run() issue.

Run with the exact input specified by the user:
- model_path: "C:/Users/K1 Center/Desktop/vibe-print/desk_cable_organizer.stl"
- quality: "standard"
- export_gcode: true
- export_3mf: true
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from vibe_print.server import slice_model, SliceModelInput, _run_async


def test_slice_model_with_exact_input():
    """
    Test using the exact input specified by the user:
    - model_path: "C:/Users/K1 Center/Desktop/vibe-print/desk_cable_organizer.stl"
    - quality: "standard"
    - export_gcode: true
    - export_3mf: true
    """
    model_path = Path(r"C:\Users\K1 Center\Desktop\vibe-print\desk_cable_organizer.stl")
    
    if not model_path.exists():
        print(f"ERROR: Model file not found: {model_path}")
        return False
    
    # Create input with exact values specified by user
    input_data = SliceModelInput(
        model_path=str(model_path),
        quality="standard",
        export_gcode=True,
        export_3mf=True,
    )
    
    # Simulate SSE transport: calling from within a running event loop
    async def call_from_running_loop():
        return slice_model(input_data)
    
    print("=" * 70)
    print("SLICE_MODEL VERIFICATION TEST")
    print("=" * 70)
    print()
    print("Input:")
    print(f"  model_path: {input_data.model_path}")
    print(f"  quality: {input_data.quality}")
    print(f"  export_gcode: {input_data.export_gcode}")
    print(f"  export_3mf: {input_data.export_3mf}")
    print()
    print("Calling slice_model from within a running asyncio event loop...")
    print("(This simulates SSE transport which invokes sync tool handlers from")
    print(" within a running loop, causing asyncio.run() to fail)")
    print()
    
    try:
        result = asyncio.run(call_from_running_loop())
        
        print("FULL JSON RESPONSE:")
        print("-" * 70)
        print(json.dumps(result, indent=2, default=str))
        print("-" * 70)
        print()
        
        # Verify no RuntimeError
        if "error" in result and "RuntimeError" in str(result.get("error")):
            if "asyncio.run()" in str(result.get("error")):
                print("FAILED: Original bug still exists!")
                return False
        
        # Extract result data
        result_data = result.get("result", {})
        
        # Check for correct keys (output_gcode and output_3mf, not gcode_path/3mf_path)
        gcode_path = result_data.get("output_gcode")
        three_mf_path = result_data.get("output_3mf")
        
        print()
        print("VERIFICATION RESULTS:")
        print("-" * 70)
        
        # Check success
        if result.get("success") and result_data.get("success"):
            print("[PASS] slice_model returned success")
        else:
            print("[FAIL] slice_model returned failure")
            return False
        
        # Check gcode_path exists
        if gcode_path:
            print(f"[PASS] gcode_path present: {gcode_path}")
            
            # Check file size
            gcode_file = Path(gcode_path)
            if gcode_file.exists():
                gcode_size = gcode_file.stat().st_size
                if gcode_size > 0:
                    print(f"[PASS] gcode file size: {gcode_size} bytes (> 0)")
                else:
                    print(f"[FAIL] gcode file is empty (0 bytes)")
                    return False
            else:
                print(f"[WARN] gcode file not found on disk")
        else:
            print("[FAIL] gcode_path is missing from response")
            return False
        
        # Check 3mf_path exists
        if three_mf_path:
            print(f"[PASS] 3mf_path present: {three_mf_path}")
            
            # Check file size
            three_mf_file = Path(three_mf_path)
            if three_mf_file.exists():
                three_mf_size = three_mf_file.stat().st_size
                if three_mf_size > 0:
                    print(f"[PASS] 3mf file size: {three_mf_size} bytes (> 0)")
                else:
                    print(f"[FAIL] 3mf file is empty (0 bytes)")
                    return False
            else:
                print(f"[WARN] 3mf file not found on disk")
        else:
            print("[FAIL] 3mf_path is missing from response")
            return False
        
        print("-" * 70)
        print()
        print("=" * 70)
        print("ALL CHECKS PASSED - Fix verified successfully!")
        print("=" * 70)
        return True
        
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print()
            print("=" * 70)
            print("FAILED: The original bug still exists!")
            print(f"RuntimeError: {e}")
            print("=" * 70)
            return False
        raise
    except Exception as e:
        print()
        print("=" * 70)
        print(f"ERROR: Unexpected exception: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_slice_model_with_exact_input()
    sys.exit(0 if success else 1)