# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely==2.1.2", "numpy==2.3.4"]
# ///
"""Compare the printable power base with the tub the rack was designed round (E2E evidence).

  uv run --script check-base-tub.py <old base_tub.stl> <new job dir> <out.json>

The old tub comes from CAD before the relief. Every deposition layer of both is sectioned in rack
x, y. Material may only go in the rear left corner behind the board, beside the two moved strap
slots and in the hole steps above the nut seats. Nothing else may differ, so the nut slots, seat
planes, screw axes, rails, comb, vents and outer faces are the old tub's. The job's G-code gives
the first layer: its clearance from the excluded corner and what it shares with the load line.
"""

import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
from shapely import LineString, Point, Polygon, box, unary_union

spec = importlib.util.spec_from_file_location("support", Path(__file__).parent / "check-support.py")
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

old_stl, job_dir, out = sys.argv[1:4]
job = Path(job_dir)
new_stl = job / "stl/base_tub.stl"
gcode = job / "base_tub/plate_1.gcode"
AREA = 0.05  # mm2: float rounding along a long outline, far below one 0.4 mm bead on any layer
HEIGHT = 96
DEPTH = 240

# Rack facts from the parts this tub must meet, none of them read from its source.
AXES = [(14, 32), (239, 32), (14, 177), (239, 177)]  # corner screws of the printed posts and decks
SEAT_Z = 90.0  # the deck stack sets the nut slot ceiling: rack z -14
BOARD = box(8, 208.5, 238, 233.5)  # D105/1 on its side, as the guide places it
RAILS_Z = (2.4, 8.4)
BEHIND_BOARD = box(3.9, 233.1, 81, 240.1)  # the rear left corner of the trough
STRAP_ZONES = [box(19.4, 75.9, 24.1, 98.1), box(142.9, 75.9, 146.6, 98.1)]
STEP_ZONES = [box(x - 2.3, y - 3.65, x + 2.3, y + 3.65) for x, y in AXES]
# M4 nut in its slot: 7 mm across flats against the slot walls, corners along the slot.
NUT_R = 3.5 / math.cos(math.radians(30))
HEX = [(NUT_R * math.cos(math.radians(a)), NUT_R * math.sin(math.radians(a))) for a in range(0, 360, 60)]


def rack_section(name, stl, to_rack):
    """Section an STL with its triangles moved into rack x, y."""
    data = Path(stl).read_bytes()
    record = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
    tri = np.frombuffer(data, dtype=record, offset=84)["v"].astype(float)
    x, y = to_rack(tri[:, :, 0], tri[:, :, 1])
    tri[:, :, 0], tri[:, :, 1] = x, y
    moved = np.zeros(len(tri), dtype=record)
    moved["v"] = tri
    path = Path(out).with_suffix(f".{name}.stl")
    path.write_bytes(data[:80] + len(tri).to_bytes(4, "little") + moved.tobytes())
    low, high = tri.min(axis=(0, 1)), tri.max(axis=(0, 1))
    size = dict(width=high[0] - low[0], depth=high[1] - low[1], height=high[2], x=low[0], y=low[1], z=0)
    return support.sectioner(path, size, np.zeros(2)), [round(float(v), 3) for v in (high - low)]


def at(sections, z):
    # Sample both meshes at one plane; move it by a few 1e-5 mm where float rounding of a cut
    # leaves a section open (a comparison plane, not a printed layer).
    for j in range(8):
        try:
            return [s(z + 0.00001 + 0.00003 * j) for s in sections]
        except ValueError:
            if j == 7:
                raise


old, old_size = rack_section("old", old_stl, lambda x, y: (x + 4, y))
new, new_size = rack_section("new", new_stl, lambda x, y: (y + 4, DEPTH - x))
sections = [old, new]
layers, ok = [], True
removed_mm3 = 0.0
unexpected = []
for k in range(HEIGHT * 5):
    z = 0.1 + 0.2 * k
    a, b = at(sections, z)
    removed, added = a.difference(b), b.difference(a)
    removed_mm3 += removed.area * 0.2
    allowed_out = [BEHIND_BOARD, *(STRAP_ZONES if z < 3.5 else [])]
    allowed_in = list(STRAP_ZONES) if z < 3.5 else []
    if SEAT_Z < z < SEAT_Z + 0.4:
        allowed_out += STEP_ZONES
    stray_out = removed.difference(unary_union(allowed_out)).area
    stray_in = added.difference(unary_union(allowed_in)).area if allowed_in else added.area
    layers.append(dict(z=round(z, 2), removed_mm2=round(removed.area, 3), added_mm2=round(added.area, 3)))
    if stray_out > AREA or stray_in > AREA:
        unexpected.append(dict(z=round(z, 2), removed_elsewhere_mm2=round(stray_out, 3), added_elsewhere_mm2=round(stray_in, 3)))
ok &= not unexpected

# Screw axes: the same 4.5 mm hole on each axis above the steps, in the old tub and the new.
axes = []
for x, y in AXES:
    row = dict(axis=[x, y])
    for name, section in (("old", old), ("new", new)):
        s = at([section], 95)[0]
        hole = next((r for g in getattr(s, "geoms", [s]) for r in g.interiors if Polygon(r).contains(Point(x, y))), None)
        row[name] = None if hole is None else dict(
            centre=[round(v, 3) for v in Polygon(hole).centroid.coords[0]], d=round(2 * math.sqrt(Polygon(hole).area / math.pi), 3))
    fits = row["old"] and row["new"] and all(abs(a - b) < 0.02 for a, b in zip(row["new"]["centre"], (x, y))) and abs(row["new"]["d"] - row["old"]["d"]) < 0.02
    ok &= bool(fits)
    axes.append(row)

# Seat planes: open air up to z 90 in each slot, the seat on the first layer above it. The strip
# moves part of the nut's bearing up by the step: reported as it is, not called unchanged.
seats = []
for x, y in AXES:
    nut = Polygon([(x + a, y + b) for a, b in HEX])
    below = at([new], SEAT_Z - 0.1)[0].intersection(nut).area
    first = [s.intersection(nut).area for s in at(sections, SEAT_Z + 0.1)]
    second = at([new], SEAT_Z + 0.3)[0].intersection(nut).area
    third = at([new], SEAT_Z + 0.5)[0].intersection(nut).area
    # beside the strip the nut bears on the seat plane; the old tub's first layer was seat everywhere
    ok &= below < AREA and first[1] > 8 and third > first[1]
    seats.append(dict(axis=[x, y], below_seat_mm2=round(below, 3), old_seat_mm2=round(first[0], 2),
                      new_seat_plane_mm2=round(first[1], 2), new_up_0_2_mm2=round(second, 2),
                      new_up_0_4_mm2=round(third, 2)))

# The board: it stands on solid rails over its whole length.
rails = []
for y0, y1 in ((209, 213), (229.6, 233.5)):
    rail = box(8, y0, 238, y1)
    missing = [round(rail.difference(at([new], z)[0]).area, 3) for z in (RAILS_Z[0] + 0.1, RAILS_Z[1] - 0.1)]
    ok &= all(m < AREA for m in missing)
    rails.append(dict(rail=[8, y0, 238, y1], missing_mm2=missing))
through_floor_old, floor_under_board = (BOARD.difference(s).area for s in at(sections, 1.3))
ok &= floor_under_board <= through_floor_old + AREA

# First layer, placed as the slicer placed it.
machine = json.loads((Path(__file__).parent / "print/machine.json").read_text())
offset = [float(v) for v in machine["extruder_offset"][0].split("x")]
points = [tuple(map(float, p.split("x"))) for p in machine["bed_exclude_area"]]
excluded = Polygon([(x - offset[0], y - offset[1]) for x, y in points])
placement = json.loads((job / "base_tub/result.json").read_text())["sliced_plates"][0]
bbox = placement["objects"][0]["bbox"]
placed = support.sectioner(new_stl, bbox, np.array(offset))
footprint = at([placed], 0.1)[0]
layer_iter = support.layers(gcode)
first_paths = next(layer_iter)
first_path = unary_union([line for line, _, _ in first_paths["paths"]])
hull_gap = round(footprint.convex_hull.distance(excluded), 3)
wall_gap = round(footprint.distance(excluded), 3)
path_gap = round(first_path.distance(excluded), 3)
# Machine start G-code: the load line runs along y 1..1.5 and has a leg up x 239.5..240 to y 11.
load_lines = [LineString([(18, 1), (240, 1), (240, 11), (239.5, 11), (239.5, 1.5), (18, 1.5)])]
shared = sum(line.intersection(footprint).length for line in load_lines)
text = gcode.read_text()
bed_probe = next((line.strip() for line in text.splitlines() if line.strip().startswith("G29 A")), None)
# Moves into the excluded corner after the start G-code; the load line itself ends on its edge.
inside_corner = excluded.buffer(-0.01)
entered = []
x = y = z = None
started = False
for raw in text.splitlines():
    if raw.startswith("; MACHINE_START_GCODE_END"):
        started = True
    if raw == "; MACHINE_END_GCODE_START":
        break
    words = dict(support.TOKEN.findall(raw.split(";", 1)[0]))
    if not raw.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
        continue
    nx, ny, nz = (float(words.get(k, v if v is not None else 0)) for k, v in zip("XYZ", (x, y, z)))
    if started and x is not None and (nx, ny) != (x, y) and LineString([(x, y), (nx, ny)]).intersects(inside_corner):
        entered.append(dict(z=nz, extrude=float(words.get("E", 0)) > 0, to=[nx, ny]))
    x, y, z = nx, ny, nz
ok &= hull_gap > 0 and wall_gap > 0 and path_gap > 0 and not entered and bed_probe is not None

result = {
    "pass": bool(ok),
    "old_size_rack": old_size,
    "new_size_rack": new_size,
    "removed_mm3": round(removed_mm3, 1),
    "unexpected": unexpected[:20],
    "screw_axes": axes,
    "nut_seats": seats,
    "rails_under_board": rails,
    "floor_openings_under_board_mm2": {"old": round(through_floor_old, 2), "new": round(floor_under_board, 2)},
    "first_layer": {
        "bed_bbox": bbox,
        "footprint_mm2": round(footprint.area, 1),
        "excluded_corner_clearance_mm": {"hull": hull_gap, "wall": wall_gap, "first_layer_path": path_gap},
        "load_line_shared_with_footprint_mm": round(shared, 2),
        "bed_probe": bed_probe,
        "moves_entering_excluded_corner": len(entered),
    },
    "layers": layers,
}
Path(out).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "layers"}))
sys.exit(0 if ok else 1)
