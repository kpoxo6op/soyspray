"""Pack the print-pack STLs into one binary blob for the browser.

Layout: uint32 header length, UTF-8 JSON header, zero padding to 4 bytes, then per part
float32 positions (centred on the part's bounding-box centre) and uint16/uint32 indices.
"""
import json, os, struct, sys
import numpy as np

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from stlinfo import load_stl

STL_DIR = os.environ['RACKSTACK'] + '/print-pack/soyspray-prototype/stl'
FILES = {
    'yBarLeft': 'QTY-2_yBarLeft.stl',
    'yBarRight': 'QTY-2_yBarRight.stl',
    'xBar': 'QTY-4_xBar.stl',
    'mainRail': 'QTY-4_mainRail.stl',
    'xyPlate': 'QTY-2_xyPlate.stl',
    'rackFeet': 'QTY-2_rackFeet.stl',
    'rackJoiner': 'QTY-4_rackJoiner.stl',
    'trayVent': 'QTY-3_m920q-ventilated-tray.stl',
    'trayUpper': 'QTY-3_upper-equipment-tray.stl',
}


def pack(stl_dir, out_path):
    header, blobs, offset = {}, [], 0
    for name, fn in FILES.items():
        tris = load_stl(f'{stl_dir}/{fn}')
        flat = tris.reshape(-1, 3)
        lo, hi = flat.min(0), flat.max(0)
        centre = (lo + hi) / 2
        key = np.round(flat, 3)
        uniq, inverse = np.unique(key, axis=0, return_inverse=True)
        idx = inverse.reshape(-1, 3)
        # drop triangles that collapse after welding
        keep = (idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])
        idx = idx[keep]
        pos = (uniq - centre).astype('<f4')
        itype = '<u2' if len(uniq) < 65536 else '<u4'
        ind = idx.astype(itype).reshape(-1)
        pb, ib = pos.tobytes(), ind.tobytes()
        pad = (-len(ib)) % 4
        header[name] = {
            'file': fn,
            'centre': [round(float(c), 4) for c in centre],
            'size': [round(float(s), 4) for s in (hi - lo)],
            'vertices': int(len(uniq)), 'triangles': int(len(idx)), 'sourceTriangles': int(len(tris)),
            'positions': [offset, len(pb)], 'indices': [offset + len(pb), len(ib)],
            'indexType': 'u16' if itype == '<u2' else 'u32',
        }
        blobs.append(pb + ib + b'\0' * pad)
        offset += len(pb) + len(ib) + pad
    hjson = json.dumps(header, separators=(',', ':')).encode()
    hpad = (-(4 + len(hjson))) % 4
    hjson += b' ' * hpad
    with open(out_path, 'wb') as f:
        f.write(struct.pack('<I', len(hjson)))
        f.write(hjson)
        for b in blobs:
            f.write(b)
    total = 4 + len(hjson) + offset
    print(f'wrote {out_path}: {total} bytes')
    for k, h in header.items():
        print(f"  {k:11s} {h['vertices']:6d} verts {h['triangles']:6d} tris (source {h['sourceTriangles']})")


if __name__ == '__main__':
    out = sys.argv[1]
    stl_dir = sys.argv[2] if len(sys.argv) > 2 else STL_DIR
    pack(stl_dir, out)
