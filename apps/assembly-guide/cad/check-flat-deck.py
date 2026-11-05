# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely==2.1.2", "numpy==2.3.4"]
# ///
"""Compare the flat mid deck print with the canonical mid deck, layer by layer (E2E evidence).

  uv run --script check-flat-deck.py <mid_deck.stl on edge> <mid_deck_flat.stl> <out.json>

The canonical deck stands on its rear edge: its bed (x, y, z) is (y, z, x) lying flat. Sections
use check-support.py's sectioner. Above the 3 mm seat plane the two must be the same solid.
Below it, nothing may be removed, and material may be added only inside the four underside post
pockets: within the seat outline that is the breakaway lattice; outside it the pocket walls are
solid, so with the lattice broken out each pocket is the seat outline, straight down to the bed.
"""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
from shapely import box, unary_union

spec = importlib.util.spec_from_file_location("support", Path(__file__).parent / "check-support.py")
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

edge_stl, flat_stl, out = sys.argv[1:4]
AREA = 0.01  # mm2: below triangle and rounding noise, far below one 0.4 mm bead per layer
SEAT = 3.0


def mesh_section(stl, permute):
    data = Path(stl).read_bytes()
    tri = np.frombuffer(
        data,
        dtype=np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")]),
        offset=84,
    )["v"].astype(float)[:, :, permute]
    path = Path(out).with_suffix(f".{Path(stl).stem}.stl")
    record = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    record["v"] = tri
    path.write_bytes(data[:80] + len(tri).to_bytes(4, "little") + record.tobytes())
    low, high = tri.min(axis=(0, 1)), tri.max(axis=(0, 1))
    size = dict(width=high[0] - low[0], depth=high[1] - low[1], height=high[2] - low[2], x=0, y=0, z=0)
    return support.sectioner(path, size, np.zeros(2)), [round(float(v), 3) for v in high - low]


edge, edge_size = mesh_section(edge_stl, [2, 0, 1])
flat, flat_size = mesh_section(flat_stl, [0, 1, 2])
# Post pockets with their feet in rack x, y, on the flat bed (209 - y, x - 4), with the old
# sloped front walls (3 mm) and a margin.
zones = [
    box(209 - y1 - 0.5, x0 - 4.5, 209 - y0 + 4.5, x1 - 3.5)
    for x0, x1 in ((4, 24), (229, 249))
    for y0, y1 in ((3, 38), (171, 206))
]
pockets = unary_union(zones)
deck = flat(SEAT + 0.1)  # the solid just above the seat planes: no pockets, only through holes
seat_outline = [z.intersection(deck).difference(edge(SEAT - 0.001)) for z in zones]
seats = unary_union(seat_outline)
layers, ok = [], edge_size == flat_size
for k in range(40):
    # Sample both meshes at one plane; move it by a few 1e-5 mm where float rounding of a cut
    # leaves a section open (a comparison plane, not a printed layer).
    for j in range(8):
        z = 0.1 + 0.2 * k + 0.00001 + 0.00003 * j
        try:
            e, f = edge(z), flat(z)
            break
        except ValueError:
            if j == 7:
                raise
    row = {"z": round(z, 5), "removed_mm2": round(e.difference(f).area, 4)}
    if z > SEAT:
        row["different_mm2"] = round(e.symmetric_difference(f).area, 4)
        ok &= row["removed_mm2"] < AREA and row["different_mm2"] < AREA
    else:
        added = f.difference(e)
        row["added_outside_pockets_mm2"] = round(added.difference(pockets).area, 4)
        # Outside the seat outline the pocket region is solid wall (or outside the deck).
        walls = pockets.difference(seats).intersection(deck)
        row["open_wall_mm2"] = round(walls.difference(f).area, 4)
        row["lattice_mm2"] = [round(s.intersection(f).area, 2) for s in seat_outline]
        ok &= (
            row["removed_mm2"] < AREA
            and row["added_outside_pockets_mm2"] < AREA
            and row["open_wall_mm2"] < AREA
            and all(a > 50 for a in row["lattice_mm2"])
        )
    layers.append(row)
result = {
    "pass": bool(ok),
    "edge_size_as_flat": edge_size,
    "flat_size": flat_size,
    "seat_outline_mm2": [round(s.area, 2) for s in seat_outline],
    "seat_outline_bounds": [[round(v, 3) for v in s.bounds] for s in seat_outline],
    "layers": layers,
}
Path(out).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "layers"}))
sys.exit(0 if ok else 1)
