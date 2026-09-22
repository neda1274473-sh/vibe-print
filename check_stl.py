import struct

with open('wall_phone_holder.stl', 'rb') as f:
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
    print('Depth (Z):', round(maxz - minz, 1), 'mm')
    print('Phone slot width:', 77, 'mm (for 75mm phone + 2mm clearance)')
    print('Phone slot depth:', 12, 'mm (for 10mm phone + 2mm clearance)')
