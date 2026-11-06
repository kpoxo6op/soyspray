# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely==2.1.2", "numpy==2.3.4"]
# ///
"""Compare the flat mid deck print with the canonical mid deck, layer by layer (E2E evidence).

  uv run --script check-flat-deck.py <mid_deck.stl on edge> <flat job dir> <out.json> [<coupon job dir>]

A job dir is a preflight output with stl/<part>.stl and <part>/plate_1.gcode. The canonical deck
stands on its rear edge: its bed (x, y, z) is (y, z, x) lying flat. Sections use check-support.py's
sectioner. Above the 3 mm seat plane the two must be the same solid. Below it, nothing may be
removed, and material may be added only inside the four underside post pockets: within the seat
outline that is the plug; outside it the pocket walls are solid, so with the plug out each pocket
is the seat outline, straight down to the bed.

The plug must stay separate from the deck in the CAD and in the actual beads: no toolpath may run
from a pocket into its wall, the beads must leave air between them, and the two layers under each
ceiling hold nothing in the pocket. The coupon must be the deck's corner on every layer, with its
ceiling bridged in the same direction.

This proves clearance in the print file. It says nothing about how easily a real plug comes out.
"""

import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
from shapely import Polygon, box, unary_union
from shapely.affinity import translate

spec = importlib.util.spec_from_file_location("support", Path(__file__).parent / "check-support.py")
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

edge_stl, flat_job, out = sys.argv[1:4]
coupon_job = sys.argv[4] if len(sys.argv) > 4 else None
AREA = 0.01  # mm2: below triangle and rounding noise, far below one 0.4 mm bead per layer
SEAT = 3.0
MIN_CAD_GAP = 0.39  # mm of air between the plug and the walls in the CAD
MIN_BEAD_GAP = 0.2  # mm of air between plug and wall beads, at their nominal widths
PLUG_TOP = 2.6  # below the seat by the two empty layers
MIN_PLUG = 30  # mm2 per pocket per layer, so a pocket cannot lose its plug unnoticed
COUPON_AT = (162, 0)  # lowest corner of the coupon on the flat deck's bed origin
OFFSET = np.array(
    [
        float(v)
        for v in json.loads((Path(__file__).parent / "print/machine.json").read_text())[
            "extruder_offset"
        ][0].split("x")
    ]
)


def mesh_section(stl, permute):
    data = Path(stl).read_bytes()
    tri = np.frombuffer(
        data,
        dtype=np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")]),
        offset=84,
    )["v"].astype(float)[:, :, permute]
    path = Path(out).with_suffix(f".{Path(stl).stem}.stl")
    record = np.zeros(
        len(tri), dtype=np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
    )
    record["v"] = tri
    path.write_bytes(data[:80] + len(tri).to_bytes(4, "little") + record.tobytes())
    low, high = tri.min(axis=(0, 1)), tri.max(axis=(0, 1))
    size = dict(
        width=high[0] - low[0], depth=high[1] - low[1], height=high[2] - low[2], x=0, y=0, z=0
    )
    return support.sectioner(path, size, np.zeros(2)), [round(float(v), 3) for v in high - low]


def beads(job, part, seats):
    """The actual toolpaths under the seat plane, per pocket: paths crossing a pocket's outline,
    the bead gap to the walls, the plug's bead area, and the ceiling's bridge direction."""
    folder = Path(job) / part
    bbox = json.loads((folder / "result.json").read_text())["sliced_plates"][0]["objects"][0]["bbox"]
    placed = [translate(s, bbox["x"] - OFFSET[0], bbox["y"] - OFFSET[1]) for s in seats]
    rows, bridge_angles = [], []
    for layer in support.layers(folder / "plate_1.gcode"):
        if layer["z"] > SEAT + 0.21:
            break
        if layer["z"] > SEAT + 0.01:
            for line, _, feature in layer["paths"]:
                inside = line.intersection(placed[0])
                if feature == "Bridge" and inside.length > 3:
                    for piece in support.pieces(inside):
                        for a, b in zip(piece.coords, piece.coords[1:]):
                            if math.dist(a, b) > 3:
                                dx, dy = b[0] - a[0], b[1] - a[1]
                                bridge_angles.append(round(math.degrees(math.atan2(dy, dx)) % 180))
            continue
        for k, seat in enumerate(placed):
            plug, wall, crossing = [], [], 0
            for line, width, _ in layer["paths"]:
                if not line.intersects(seat.buffer(3)):
                    continue
                inner = line.intersection(seat).length
                outer = line.difference(seat).length
                if inner > support.TOL and outer > support.TOL:
                    crossing += 1
                (plug if inner > outer else wall).append(line.buffer(width / 2, quad_segs=3))
            plug, wall = unary_union(plug), unary_union(wall)
            rows.append(
                dict(
                    z=layer["z"],
                    pocket=k,
                    crossing_paths=crossing,
                    plug_beads_mm2=round(plug.area, 2),
                    bead_gap_mm=round(plug.distance(wall), 3) if not plug.is_empty else None,
                )
            )
    return rows, sorted(set(bridge_angles))


edge, edge_size = mesh_section(edge_stl, [2, 0, 1])
flat, flat_size = mesh_section(Path(flat_job) / "stl/mid_deck_flat.stl", [0, 1, 2])
# Post pockets with their feet in rack x, y, on the flat bed (209 - y, x - 4), with the old
# sloped front walls (3 mm) and a margin.
zones = [
    box(209 - y1 - 0.5, x0 - 4.5, 209 - y0 + 4.5, x1 - 3.5)
    for x0, x1 in ((4, 24), (229, 249))
    for y0, y1 in ((3, 38), (171, 206))
]
pockets = unary_union(zones)
deck = flat(SEAT + 0.1)  # the solid just above the seat planes: no pockets, only through holes


def outline(zone):
    """The pocket at its seat, its screw hole filled, without the hairline rounding differences
    between the two meshes along the deck's plan corners."""
    area = zone.intersection(deck).difference(edge(SEAT - 0.001))
    area = area.buffer(-0.1, join_style="mitre").buffer(0.1, join_style="mitre")
    largest = max(getattr(area, "geoms", [area]), key=lambda g: g.area)
    return Polygon(largest.exterior)


seat_outline = [outline(z) for z in zones]
seats = unary_union(seat_outline)
walls = pockets.difference(seats).intersection(deck)
layers, ok = [], edge_size == flat_size
contact, plug_top = [], []
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
        # 0.05 mm in from the outline, clear of float slivers of wall along it
        plugs = [s.buffer(-0.05, join_style="mitre").intersection(f) for s in seat_outline]
        solid = f.intersection(walls)
        row["added_outside_pockets_mm2"] = round(added.difference(pockets).area, 4)
        # Outside the seat outline the pocket region is solid wall (or outside the deck).
        row["open_wall_mm2"] = round(walls.difference(f).area, 4)
        row["plug_mm2"] = [round(p.area, 2) for p in plugs]
        # measured to the wall, so the 0.05 mm is not counted as air
        row["plug_wall_gap_mm"] = [round(p.distance(solid), 3) for p in plugs if not p.is_empty]
        ok &= (
            row["removed_mm2"] < AREA
            and row["added_outside_pockets_mm2"] < AREA
            and row["open_wall_mm2"] < AREA
            and all(g >= MIN_CAD_GAP for g in row["plug_wall_gap_mm"])
        )
        if z < PLUG_TOP:
            plug_top = row["plug_mm2"]
            ok &= all(a > MIN_PLUG for a in row["plug_mm2"])
        else:
            contact = row["plug_mm2"]
            ok &= all(a < AREA for a in row["plug_mm2"])
    layers.append(row)
flat_beads, flat_angles = beads(flat_job, "mid_deck_flat", seat_outline)


def beads_ok(rows):
    return all(
        r["crossing_paths"] == 0
        and (
            r["bead_gap_mm"] is not None
            and r["bead_gap_mm"] >= MIN_BEAD_GAP
            and r["plug_beads_mm2"] > MIN_PLUG
            if r["z"] < PLUG_TOP + 0.01
            else r["plug_beads_mm2"] == 0
        )
        for r in rows
    )


ok &= len(flat_beads) == 60 and beads_ok(flat_beads)
result = {
    "edge_size_as_flat": edge_size,
    "flat_size": flat_size,
    "seat_outline_mm2": [round(s.area, 2) for s in seat_outline],
    "seat_outline_bounds": [[round(v, 3) for v in s.bounds] for s in seat_outline],
    "plug_top_cad_mm2": plug_top,
    "plug_contact_cad_mm2": contact,
    "plug_contact_beads_mm2": [r["plug_beads_mm2"] for r in flat_beads if abs(r["z"] - SEAT) < 0.01],
    "min_cad_gap_mm": min((g for r in layers for g in r.get("plug_wall_gap_mm", [])), default=None),
    "min_bead_gap_mm": min((r["bead_gap_mm"] for r in flat_beads if r["bead_gap_mm"] is not None), default=None),
    "first_layer_bead_gap_mm": [r["bead_gap_mm"] for r in flat_beads[:4]],
    "crossing_paths": sum(r["crossing_paths"] for r in flat_beads),
    "ceiling_bridge_angles_deg": flat_angles,
}
if coupon_job:
    coupon, coupon_size = mesh_section(Path(coupon_job) / "stl/mid_deck_pocket_coupon.stl", [0, 1, 2])
    cut = box(*COUPON_AT, COUPON_AT[0] + coupon_size[0], COUPON_AT[1] + coupon_size[1])
    different = 0.0
    for k in range(40):
        for j in range(8):
            z = 0.1 + 0.2 * k + 0.00001 + 0.00003 * j
            try:
                c = translate(coupon(z), *COUPON_AT)
                f = flat(z).intersection(cut)
                break
            except ValueError:
                if j == 7:
                    raise
        different = max(different, c.symmetric_difference(f).area)
    # The front left pocket is the deck's seat at x > 100, y < 100.
    corner = [s for s in seat_outline if s.bounds[0] > 100 and s.bounds[1] < 100][0]
    coupon_beads, coupon_angles = beads(
        coupon_job, "mid_deck_pocket_coupon", [translate(corner, -COUPON_AT[0], -COUPON_AT[1])]
    )
    deck_angles = beads(flat_job, "mid_deck_flat", [corner])[1]
    result["coupon"] = {
        "size": coupon_size,
        "max_section_difference_mm2": round(different, 4),
        "min_bead_gap_mm": min(
            (r["bead_gap_mm"] for r in coupon_beads if r["bead_gap_mm"] is not None), default=None
        ),
        "crossing_paths": sum(r["crossing_paths"] for r in coupon_beads),
        "ceiling_bridge_angles_deg": coupon_angles,
        "deck_corner_bridge_angles_deg": deck_angles,
    }
    ok &= (
        different < AREA
        and len(coupon_beads) == 15
        and beads_ok(coupon_beads)
        and result["coupon"]["crossing_paths"] == 0
        and coupon_angles == deck_angles
        and len(coupon_angles) > 0
    )
result = {"pass": bool(ok), **result, "layers": layers, "beads": flat_beads}
Path(out).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("layers", "beads")}))
sys.exit(0 if ok else 1)
