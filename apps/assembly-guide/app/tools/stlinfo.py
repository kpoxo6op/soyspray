import sys, struct, numpy as np

def load_stl(path):
    data = open(path, 'rb').read()
    if data[:5] == b'solid' and b'facet' in data[:300]:
        # ASCII
        verts = []
        for line in data.decode('ascii', 'replace').splitlines():
            line = line.strip()
            if line.startswith('vertex'):
                verts.append([float(x) for x in line.split()[1:4]])
        v = np.array(verts, dtype=np.float64).reshape(-1, 3, 3)
        return v
    n = struct.unpack('<I', data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
    return arr['v'].astype(np.float64)

if __name__ == '__main__':
    for p in sys.argv[1:]:
        tris = load_stl(p)
        v = tris.reshape(-1, 3)
        print(p.split('/')[-1], 'tris', len(tris), 'min', np.round(v.min(0), 3), 'max', np.round(v.max(0), 3), 'size', np.round(v.max(0) - v.min(0), 3))
