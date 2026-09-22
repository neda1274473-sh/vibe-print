"""
Desk Cable Organizer Generator

Generates a simple desk cable organizer with three cable slots.
The design features a weighted base with curved cable channels
for routing and organizing cables on a desk.

Output: desk_cable_organizer.stl
"""

import cadquery as cq
from pathlib import Path

# -------------------------------
# Dimensions (all in mm)
# -------------------------------
# Overall organizer dimensions
ORGANIZER_WIDTH = 120.0   # X dimension
ORGANIZER_DEPTH = 40.0     # Y dimension  
ORGANIZER_HEIGHT = 16.0    # Z dimension (includes slot depth)

# Base plate
BASE_THICKNESS = 5.0

# Cable slot parameters
NUM_SLOTS = 3
SLOT_WIDTH = 8.0           # Width of each cable channel
SLOT_SPACING = 28.0        # Center-to-center spacing between slots
SLOT_DEPTH = 10.0          # How deep each slot is cut into the top
WALL_THICKNESS = 4.0       # Wall between slots and outer edges

# Cable slot profile
SLOT_RADIUS = 4.5          # Radius of the rounded cable channel


def generate_desk_cable_organizer(output_path: Path):
    """Generate the desk cable organizer STL with three cable slots."""
    
    # -------------------------------
    # 1. Create the base body
    # -------------------------------
    # Main rectangular body
    body = cq.Workplane("XY").box(
        ORGANIZER_WIDTH,
        ORGANIZER_DEPTH,
        ORGANIZER_HEIGHT
    )
    
    # -------------------------------
    # 2. Calculate slot positions (centered on X axis)
    # -------------------------------
    # Total width needed for 3 slots with walls
    total_slots_width = (NUM_SLOTS * SLOT_WIDTH) + ((NUM_SLOTS - 1) * WALL_THICKNESS)
    start_x = -total_slots_width / 2 + SLOT_WIDTH / 2
    
    slot_x_positions = []
    for i in range(NUM_SLOTS):
        x_pos = start_x + i * (SLOT_WIDTH + WALL_THICKNESS)
        slot_x_positions.append(x_pos)
    
    # -------------------------------
    # 3. Cut the three cable slots
    # -------------------------------
    for x_pos in slot_x_positions:
        # Create a D-shaped slot (rectangle with rounded bottom)
        # The slot is positioned at the top of the body
        
        # Add rounded bottom to the slot (cylindrical cutout)
        round_bottom = (
            cq.Workplane("XY")
            .workplane(offset=ORGANIZER_HEIGHT / 2 - SLOT_DEPTH / 2)
            .center(x_pos, 0)
            .circle(SLOT_RADIUS)
            .extrude(ORGANIZER_DEPTH + 2)
        )
        body = body.cut(round_bottom)
    
    # -------------------------------
    # 4. Export to STL
    # -------------------------------
    cq.exporters.export(body, str(output_path))
    print(f"Exported desk cable organizer to: {output_path}")
    
    # Print summary
    print(f"\n--- Cable Organizer Summary ---")
    print(f"Overall Dimensions: {ORGANIZER_WIDTH} x {ORGANIZER_DEPTH} x {ORGANIZER_HEIGHT} mm")
    print(f"Cable slots: {NUM_SLOTS}")
    print(f"Slot width: {SLOT_WIDTH} mm")
    print(f"Slot radius: {SLOT_RADIUS} mm")
    print(f"Suitable for cables up to ~{SLOT_RADIUS * 1.6:.0f} mm diameter")
    
    return output_path


if __name__ == "__main__":
    output = Path("desk_cable_organizer.stl")
    generate_desk_cable_organizer(output)
    print(f"\nDone! File saved as {output.absolute()}")e with three evenly-spaced circular holes
designed to hold standard pens and pencils.

Output: desk_pen_organizer.stl
"""

import cadquery as cq
from pathlib import Path

# -------------------------------
# Dimensions (all in mm)
# -------------------------------
# Overall organizer dimensions
ORGANIZER_WIDTH = 150.0   # X dimension
ORGANIZER_DEPTH = 50.0    # Y dimension  
ORGANIZER_HEIGHT = 45.0   # Z dimension (total height)

# Base plate for stability
BASE_THICKNESS = 8.0
BASE_FOOTPRINT = 15.0     # Extra width/depth on base for stability

# Pen holder parameters
NUM_HOLDERS = 3
HOLDER_DIAMETER = 14.0    # Inner diameter for pen holes
HOLDER_DEPTH = 35.0       # How deep each hole goes
WALL_THICKNESS = 6.0      # Wall between holders and outer edges
HOLDER_SPACING = 35.0     # Center-to-center spacing between holders

# Bottom thickness (from base to start of holes)
BOTTOM_THICKNESS = ORGANIZER_HEIGHT - HOLDER_DEPTH


def generate_desk_pen_organizer(output_path: Path):
    """Generate the desk pen organizer STL with three pen holders."""
    
    # -------------------------------
    # 1. Create the main body
    # -------------------------------
    # Tapered rectangular body (wider at bottom for stability)
    body = (
        cq.Workplane("XY")
        .workplane(offset=BASE_THICKNESS)
        .rect(ORGANIZER_WIDTH - 10, ORGANIZER_DEPTH - 5)
        .extrude(ORGANIZER_HEIGHT - BASE_THICKNESS)
    )
    
    # Add the stable base
    base = (
        cq.Workplane("XY")
        .box(
            ORGANIZER_WIDTH + BASE_FOOTPRINT,
            ORGANIZER_DEPTH + BASE_FOOTPRINT,
            BASE_THICKNESS
        )
    )
    
    # Combine body and base
    body = body.union(base)
    
    # -------------------------------
    # 2. Calculate holder positions (centered on X and Y axes)
    # -------------------------------
    total_holders_width = (NUM_HOLDERS - 1) * HOLDER_SPACING
    start_x = -total_holders_width / 2
    
    holder_x_positions = []
    for i in range(NUM_HOLDERS):
        x_pos = start_x + i * HOLDER_SPACING
        holder_x_positions.append(x_pos)
    
    # -------------------------------
    # 3. Create and cut the three pen holder holes
    # -------------------------------
    for x_pos in holder_x_positions:
        # Create a cylindrical hole for pen holder
        # Positioned at the top of the body
        holder_hole = (
            cq.Workplane("XY")
            .workplane(offset=BASE_THICKNESS + 5)
            .center(x_pos, 0)
            .circle(HOLDER_DIAMETER / 2)
            .extrude(HOLDER_DEPTH + 10)
        )
        body = body.cut(holder_hole)
    
    # -------------------------------
    # 4. Add a decorative rim at the top
    # -------------------------------
    rim_thickness = 3.0
    rim = (
        cq.Workplane("XY")
        .workplane(offset=ORGANIZER_HEIGHT - rim_thickness)
        .rect(ORGANIZER_WIDTH, ORGANIZER_DEPTH)
        .extrude(rim_thickness)
    )
    body = body.cut(rim)
    
    # -------------------------------
    # 5. Add a curved handle/scoop at the front
    # -------------------------------
    # Creates an easy access curve at the front for grabbing pens
    front_scoop = (
        cq.Workplane("XZ")
        .workplane(offset=0)
        .center(0, ORGANIZER_HEIGHT / 2 + 5)
        .rect(ORGANIZER_WIDTH + BASE_FOOTPRINT, 15)
        .extrude(25)
    )
    body = body.cut(front_scoop)
    
    # -------------------------------
    # 6. Export to STL
    # -------------------------------
    cq.exporters.export(body, str(output_path))
    print(f"Exported desk pen organizer to: {output_path}")
    
    # Print summary
    print(f"\n--- Pen Organizer Summary ---")
    print(f"Overall Dimensions: {ORGANIZER_WIDTH + BASE_FOOTPRINT} x {ORGANIZER_DEPTH + BASE_FOOTPRINT} x {ORGANIZER_HEIGHT} mm")
    print(f"Base dimensions: {ORGANIZER_WIDTH + BASE_FOOTPRINT} x {ORGANIZER_DEPTH + BASE_FOOTPRINT} x {BASE_THICKNESS} mm")
    print(f"Pen holders: {NUM_HOLDERS}")
    print(f"Hole diameter: {HOLDER_DIAMETER} mm")
    print(f"Hole depth: {HOLDER_DEPTH} mm")
    print(f"Holder spacing: {HOLDER_SPACING} mm center-to-center")
    print(f"Suitable for pens up to ~{HOLDER_DIAMETER - 2} mm diameter")
    print(f"Recommended print settings: 0.2mm layer height, 20% infill, no supports needed")
    
    return output_path


if __name__ == "__main__":
    output = Path("desk_pen_organizer.stl")
    generate_desk_pen_organizer(output)
    print(f"\nDone! File saved as {output.absolute()}")