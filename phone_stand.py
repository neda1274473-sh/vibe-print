"""
Tabletop Phone Stand Generator

Generates a small phone stand with:
- Rectangular base (stable on a table)
- Back support inclined at exactly 60 degrees from the base plane
- A small lip at the bottom to prevent the phone from sliding off

Output: phone_stand.stl
"""

import cadquery as cq
import math
from pathlib import Path

# -------------------------------
# Dimensions (all in mm)
# -------------------------------
# Base plate
BASE_WIDTH = 80.0
BASE_DEPTH = 60.0
BASE_THICKNESS = 4.0

# Back support (triangular wedge inclined at 60 degrees from horizontal)
SUPPORT_ANGLE_DEG = 60.0        # angle from horizontal base plane
SUPPORT_HEIGHT = 70.0           # vertical height of the support
SUPPORT_THICKNESS = 6.0          # thickness of the wedge

# Lip (small shelf at bottom to prevent phone from sliding)
LIP_HEIGHT = 6.0
LIP_DEPTH = 3.0

# Fillets
OUTER_FILLET = 1.5


def generate_phone_stand(output_path: Path):
    """Generate the phone stand STL."""
    # -------------------------------
    # 1. Base plate (centered on XY)
    # -------------------------------
    base = cq.Workplane("XY").box(BASE_WIDTH, BASE_DEPTH, BASE_THICKNESS)

    # -------------------------------
    # 2. Back support wedge at 60 degrees
    # -------------------------------
    # For 60 degrees from horizontal:
    #   - Vertical rise = SUPPORT_HEIGHT
    #   - Horizontal reach = SUPPORT_HEIGHT / tan(60°) = SUPPORT_HEIGHT / 1.732
    #
    # Sketch in YZ plane:
    #   (0, 0)               -> front bottom (meets the base)
    #   (0, SUPPORT_HEIGHT)   -> front top (phone rests here)
    #   (reach, 0)           -> back bottom (ground contact)
    reach = SUPPORT_HEIGHT / math.tan(math.radians(SUPPORT_ANGLE_DEG))

    wedge = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(0, SUPPORT_HEIGHT)
        .lineTo(reach, 0)
        .close()
        .extrude(BASE_WIDTH / 2, both=True)   # extrude +/-X to full width
    )

    # Position wedge so its front bottom edge sits at the back edge of the base.
    # Base extends from Y = -BASE_DEPTH/2 to +BASE_DEPTH/2.
    # We shift the wedge back by BASE_DEPTH/2 along Y, and up by BASE_THICKNESS/2
    # along Z so it sits flush on top of the base.
    wedge = wedge.translate((0, -BASE_DEPTH / 2, BASE_THICKNESS / 2))

    # Combine base + wedge
    stand = base.union(wedge)

    # -------------------------------
    # 3. Bottom lip (small shelf to stop phone from sliding)
    # -------------------------------
    lip = (
        cq.Workplane("XY")
        .workplane(offset=BASE_THICKNESS / 2)
        .center(0, -BASE_DEPTH / 2 + LIP_DEPTH / 2)
        .box(BASE_WIDTH - 4, LIP_DEPTH, LIP_HEIGHT)
    )
    stand = stand.union(lip)

    # -------------------------------
    # 4. Round top edges for comfort
    # -------------------------------
    try:
        stand = stand.edges(">Z").fillet(OUTER_FILLET)
    except Exception:
        pass

    # -------------------------------
    # 5. Export
    # -------------------------------
    cq.exporters.export(stand, str(output_path))
    print(f"Exported phone stand to: {output_path}")
    return output_path


if __name__ == "__main__":
    output = Path("phone_stand.stl")
    generate_phone_stand(output)
    print(f"Done! File saved as {output.absolute()}")
