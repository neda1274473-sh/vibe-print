import struct

with open('mounting_plate.stl', 'rb') as f:
    f.read(80)
    num = struct.unpack('<I', f.read(4))[0]
    minx = miny = minz = float('inf')
    maxx = maxy = maxz = float('-inf')
    for _ in range(num):
        f.read(12)
        for _ in range(3):
            x, y, z = struct.unpack('<fff', f.read(12))
            minx, maxx = min(minx, x), max(maxx, x)
            miny, maxy = min(miny, y), max(maxy, y)
            minz, maxz = min(minz, z), max(maxz, z)
        f.read(2)

    print('Width (X):', round(maxx - minx, 1), 'mm')
    print('Height (Y):', round(maxy - miny, 1), 'mm')
    print('Depth/Thickness (Z):', round(maxz - minz, 1), 'mm')
    print('Triangles:', num)
    print('')
    print('Design specs:')
    print('  Plate: 80mm x 50mm x 3mm')
    print('  4x M4 screw holes (4.5mm dia) with countersinks')
    print('  Hole inset: 8mm from edges')
