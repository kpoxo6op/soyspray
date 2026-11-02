# /// script
# requires-python = ">=3.12"
# dependencies = ["shapely==2.1.2", "numpy==2.3.4"]
# ///
"""Check placed CAD sections against ACTUAL deposition paths, independent of slicer warnings.

P1S / single nozzle / planar Bambu G-code only. Unknown extrusion coordinates,
nonplanar layers and unsupported paths reject the job. End-anchored gap-spanning
bridges up to 8 mm are admitted; longer spans require a design/qualification
change rather than an operator 'ignore warning' flag. This does not measure
adhesion, filament condition, cooling or strength.
"""

import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from shapely import LineString, Point, Polygon, MultiLineString, build_area
from shapely.affinity import translate

VERSION = 1
MAX_BRIDGE = 8.0
TOL = 0.04  # coordinate/arc tessellation tolerance, mm
TOKEN = re.compile(r"([A-Z])(-?(?:\d+(?:\.\d*)?|\.\d+))")


def layers(path):
    x = y = z = e = 0.0
    relative_e = False
    absolute_xyz = True
    width = None
    layer = None
    feature = ""
    points = []
    paths = []
    n = 0
    after_start = False  # past MACHINE_START_GCODE_END: any deposition now is the model's

    def flush():
        nonlocal points
        if len(points) > 1:
            paths.append((LineString(points), width, feature))
        points = []

    for lineno, raw in enumerate(Path(path).read_text().splitlines(), 1):
        if raw == "; MACHINE_END_GCODE_START":
            break
        if raw.startswith("; MACHINE_START_GCODE_END"):
            after_start = True
        if raw.startswith("; CHANGE_LAYER"):
            flush()
            if layer is not None:
                yield {"number": n, "z": layer, "paths": paths}
            layer = None
            paths = []
            n += 1
        elif raw.startswith("; Z_HEIGHT:"):
            layer = float(raw.split(":", 1)[1])
        elif raw.startswith("; LINE_WIDTH:"):
            flush()
            width = float(raw.split(":", 1)[1])
        elif raw.startswith("; FEATURE:"):
            flush()
            feature = raw.split(":", 1)[1].strip()
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        cmd = line.split()[0]
        args = {k: float(v) for k, v in TOKEN.findall(line[len(cmd) :])}
        if not all(math.isfinite(v) for v in args.values()):
            raise ValueError(f"nonfinite value at line {lineno}")
        if cmd == "M83":
            relative_e = True
        elif cmd == "M82":
            relative_e = False
        elif cmd == "G90":
            absolute_xyz = True
        elif cmd == "G91":
            absolute_xyz = False
        elif cmd == "G92":
            x, y, z, e = (args.get(k, v) for k, v in zip("XYZE", (x, y, z, e)))
        elif cmd in ("G0", "G1", "G2", "G3"):
            nx, ny, nz = (
                args.get(k, v) if absolute_xyz else v + args.get(k, 0)
                for k, v in zip("XYZ", (x, y, z))
            )
            de = args.get("E", 0) if relative_e else args.get("E", e) - e
            e = e + args.get("E", 0) if relative_e else args.get("E", e)
            moving = math.hypot(nx - x, ny - y) > 1e-7 or (
                cmd in ("G2", "G3") and ("I" in args or "J" in args)
            )
            if de > 1e-7 and moving and (layer is None and (n or after_start)):
                # Model deposition must be attributable to a layer; never skip it unchecked.
                raise ValueError(f"deposition outside a known layer at line {lineno}")
            if n and layer is not None and de > 1e-7 and moving:
                if not absolute_xyz or abs(nz - layer) > TOL or abs(z - layer) > TOL:
                    raise ValueError(f"nonplanar/relative deposition at line {lineno}")
                if width is None or not 0.05 <= width <= 1.2:
                    raise ValueError(f"unknown extrusion width at line {lineno}")
                if not points:
                    points.append((x, y))
                if cmd in ("G2", "G3"):
                    if "R" in args or not ("I" in args or "J" in args):
                        raise ValueError(f"unsupported arc at line {lineno}")
                    cx, cy = x + args.get("I", 0), y + args.get("J", 0)
                    radius = math.hypot(x - cx, y - cy)
                    if radius <= 0 or abs(math.hypot(nx - cx, ny - cy) - radius) > 0.1:
                        raise ValueError(f"inconsistent arc at line {lineno}")
                    start, end = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                    sweep = (
                        (end - start) % (2 * math.pi)
                        if cmd == "G3"
                        else -((start - end) % (2 * math.pi))
                    )
                    if abs(sweep) < 1e-9:
                        sweep = 2 * math.pi if cmd == "G3" else -2 * math.pi
                    steps = max(2, math.ceil(abs(sweep) * radius / 0.25))
                    points.extend(
                        (
                            cx + radius * math.cos(start + sweep * j / steps),
                            cy + radius * math.sin(start + sweep * j / steps),
                        )
                        for j in range(1, steps)
                    )
                points.append((nx, ny))
            else:
                flush()
            x, y, z = nx, ny, nz
        elif n and cmd.startswith("G") and cmd not in ("G17",):
            raise ValueError(f"unsupported in-layer command {cmd} at line {lineno}")
    flush()
    if layer is not None:
        yield {"number": n, "z": layer, "paths": paths}


def pieces(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in pieces(g)]
    raise ValueError(f"unexpected path geometry {geom.geom_type}")


def sectioner(stl, bbox, tool_offset):
    data = Path(stl).read_bytes()
    if len(data) < 84:
        raise ValueError("not a binary STL")
    count = int.from_bytes(data[80:84], "little")
    if len(data) != 84 + 50 * count or count == 0:
        raise ValueError("malformed or empty STL")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    tri = np.frombuffer(data, dtype=dtype, offset=84)["vertices"].astype(float)
    if not np.isfinite(tri).all():
        raise ValueError("nonfinite mesh")
    low, high = tri.min(axis=(0, 1)), tri.max(axis=(0, 1))
    if any(
        abs(high[i] - low[i] - bbox[key]) > 0.02
        for i, key in enumerate(("width", "depth", "height"))
    ):
        raise ValueError("slicer changed model orientation or scale")
    if abs(low[2]) > TOL or abs(bbox["z"]) > TOL:
        raise ValueError("model is not on bed")
    tri[:, :, :2] += np.array([bbox["x"], bbox["y"]]) - low[:2] - tool_offset
    starts = tri[:, [0, 1, 2], :]
    ends = tri[:, [1, 2, 0], :]

    def section(z):
        crossing = (starts[:, :, 2] > z) != (ends[:, :, 2] > z)
        rows = np.where(crossing.sum(axis=1) == 2)[0]
        edges = crossing[rows]
        a, b = starts[rows][edges], ends[rows][edges]
        points = a[:, :2] + ((z - a[:, 2]) / (b[:, 2] - a[:, 2]))[:, None] * (b[:, :2] - a[:, :2])
        segments = np.round(points.reshape(-1, 2, 2), 5)
        area = build_area(MultiLineString(segments.tolist())) if len(segments) else Polygon()
        if area.is_empty or not area.is_valid:
            raise ValueError(f"cannot reconstruct solid section at z={z}")
        # Every cut segment must end up on the section boundary. Linework that did not close
        # is dropped by build_area, which could turn a hole into material under a bridge.
        linework = float(np.hypot(*(segments[:, 1] - segments[:, 0]).T).sum())
        if abs(area.boundary.length - linework) > max(1e-3, 1e-6 * linework):
            raise ValueError(f"section linework does not close into a solid at z={z}")
        return area

    return section


def check(path, stl, result_path):
    machine = json.loads((Path(__file__).parent / "print/machine.json").read_text())
    if machine["printer_model"] != "Bambu Lab P1S" or machine["nozzle_diameter"] != ["0.4"]:
        raise ValueError("unsupported printer/nozzle policy")
    offset = np.array([float(x) for x in machine["extruder_offset"][0].split("x")])
    points = lambda key: [tuple(map(float, p.split("x"))) for p in machine[key]]
    bed = Polygon(points("printable_area")).difference(Polygon(points("bed_exclude_area")))
    bed = translate(bed, xoff=-offset[0], yoff=-offset[1])
    result = json.loads(Path(result_path).read_text())
    plates = result["sliced_plates"]
    if len(plates) != 1 or len(plates[0]["objects"]) != 1:
        raise ValueError("one object/plate required for this policy")
    section = sectioner(stl, plates[0]["objects"][0]["bbox"], offset)
    previous = Polygon()
    previous_z = 0.0
    failures, bridges = [], []
    checked = 0
    for layer in layers(path):
        checked += 1
        n, z, paths = layer["number"], layer["z"], layer["paths"]
        height = z - previous_z
        if not paths or not 0.05 <= height <= 0.28 + TOL:
            raise ValueError(f"empty or unsupported layer step {n}: {height:.3f} mm")
        current = section(z - height / 2 + 0.00001)
        if not bed.buffer(TOL).covers(current) or z > float(machine["printable_height"]):
            raise ValueError(f"layer {n} conflicts with printer volume/excluded corner")
        # Structural solid from the preceding CAD slice, not a filled projection of
        # the whole object. This preserves designed infill cavities but never treats
        # a vent/window outside that slice as material. Cross-check actual toolpaths
        # against the placed section so a stale/rotated/different job cannot use it.
        support = previous.buffer(height + TOL, quad_segs=3)
        accepted = []
        for line, width, feature in paths:
            if not current.buffer(TOL * 2).covers(line):
                raise ValueError(f"toolpath outside placed model at layer {n} ({feature})")
            if checked == 1:
                continue
            failures_before = len(failures)
            for air in pieces(line.difference(support)):
                length = air.length
                if length <= TOL:
                    continue
                a, b = Point(air.coords[0]), Point(air.coords[-1])

                def anchor(point):
                    return point.distance(support) < TOL or any(
                        point.distance(p) <= width / 2 + TOL for p in accepted
                    )

                anchored = anchor(a) and anchor(b)
                # A bent bridge may span a rounded opening. A loop back to the same
                # anchor is a cantilever, not a two-ended bridge.
                spans_gap = a.distance(b) >= length * 0.5
                item = {
                    "layer": n,
                    "z": z,
                    "feature": feature,
                    "unsupported_mm": round(length, 3),
                    "end_anchors": anchored,
                    "spans_gap": spans_gap,
                    "from": list(air.coords[0]),
                    "to": list(air.coords[-1]),
                }
                if anchored and spans_gap and length <= MAX_BRIDGE:
                    bridges.append(item)
                else:
                    failures.append(item)
            if len(failures) == failures_before:
                accepted.append(line.buffer(width / 2, quad_segs=3))
        previous = current
        previous_z = z
    if not checked:
        raise ValueError("no deposition layers")
    return {
        "policy_version": VERSION,
        "pass": not failures,
        "layers_checked": checked,
        "max_bridge_mm": MAX_BRIDGE,
        "failures": failures,
        "bridges": bridges,
    }


if __name__ == "__main__":
    try:
        result = check(sys.argv[1], sys.argv[2], sys.argv[3])
    except Exception as error:
        result = {"policy_version": VERSION, "pass": False, "error": str(error)}
    Path(sys.argv[4]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("failures", "bridges")}))
    sys.exit(0 if result["pass"] else 1)
