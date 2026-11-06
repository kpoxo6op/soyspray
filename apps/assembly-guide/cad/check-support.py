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

A part named in RELEASE_INTERFACES is judged by policy 2, and says so. Its separate plugs stand under
ceilings that must not fuse to them. For that part alone, the plug's top counts as support for the first ceiling layer across a
declared air gap, and the 8 mm span rule then applies between its fins. The same part must keep
that air empty, keep each plug clear of its walls in the CAD and in the beads, keep the ceiling's
beads above the plug and lay its first layer clear of the machine's load line. This limits how a
print file may be built. It cannot show how hard a real plug is to remove.
"""

import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from shapely import LineString, MultiLineString, Point, Polygon, box, build_area, unary_union
from shapely.affinity import translate

VERSION = 1
RELEASE_VERSION = 2
MAX_BRIDGE = 8.0
TOL = 0.04  # coordinate/arc tessellation tolerance, mm
TOKEN = re.compile(r"([A-Z])(-?(?:\d+(?:\.\d*)?|\.\d+))")
START_END = "; MACHINE_START_GCODE_END"
# Part name -> release interface. Zones are the pocket outlines' bounds on the part's own plan, from
# its lowest corner. Two empty 0.2 mm layers: the sliced ceiling beads, round and hanging from the
# nozzle, are 0.29 mm above the fins. Over one empty layer they would be 0.09 mm above, below this
# limit, so the smallest sag would land them. Slicer support would need a whole-pocket interface.
_GAP = dict(
    ceiling_z=3.0,
    air_layers=2,
    layer_height=0.2,
    min_wall_gap_mm=0.39,  # CAD air between a plug and the deck
    min_bead_gap_mm=0.2,  # air between plug and deck beads at their nominal widths
    min_bead_clearance_mm=0.15,  # hanging ceiling bead above the plug, before any sag
    min_start_clearance_mm=1.0,  # first layer beads from load line beads
)
RELEASE_INTERFACES = {
    "mid_deck_flat": _GAP
    | {
        "zones": [
            (170.75, 0.0, 206.251, 20.25),
            (2.75, 0.0, 38.251, 20.25),
            (170.75, 224.75, 206.251, 245.0),
            (2.75, 224.75, 38.251, 245.0),
        ]
    },
    "mid_deck_pocket_coupon": _GAP | {"zones": [(8.75, 0.0, 44.251, 20.25)]},
}


def layers(path):
    x = y = z = e = 0.0
    relative_e = False
    absolute_xyz = True
    width = None
    layer = None
    feature = ""
    points = []
    paths = []
    flows = []  # per path, the largest filament mm per mm of any segment over 0.5 mm
    peak = 0.0
    n = 0
    after_start = False  # past MACHINE_START_GCODE_END: any deposition now is the model's

    def flush():
        nonlocal points, peak
        if len(points) > 1:
            paths.append((LineString(points), width, feature))
            flows.append(peak)
        points = []
        peak = 0.0

    for lineno, raw in enumerate(Path(path).read_text().splitlines(), 1):
        if raw == "; MACHINE_END_GCODE_START":
            break
        if raw.startswith("; MACHINE_START_GCODE_END"):
            after_start = True
        if raw.startswith("; CHANGE_LAYER"):
            flush()
            if layer is not None:
                yield {"number": n, "z": layer, "paths": paths, "flows": flows}
            layer = None
            paths = []
            flows = []
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
                run = math.hypot(nx - x, ny - y)
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
                    run = abs(sweep) * radius
                    steps = max(2, math.ceil(run / 0.25))
                    points.extend(
                        (
                            cx + radius * math.cos(start + sweep * j / steps),
                            cy + radius * math.sin(start + sweep * j / steps),
                        )
                        for j in range(1, steps)
                    )
                points.append((nx, ny))
                if run > 0.5:
                    peak = max(peak, de / run)
            else:
                flush()
            x, y, z = nx, ny, nz
        elif n and cmd.startswith("G") and cmd not in ("G17",):
            raise ValueError(f"unsupported in-layer command {cmd} at line {lineno}")
    flush()
    if layer is not None:
        yield {"number": n, "z": layer, "paths": paths, "flows": flows}


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


def start_strokes(path, filament_area):
    """The machine start G-code's deposited strokes near the bed, as beads in tool coordinates:
    the stock load line. Its cleaning strokes deposit nothing and run on steel outside the bed."""
    x = y = z = e = 0.0
    relative_e = False
    absolute_xyz = True
    strokes = []
    for raw in Path(path).read_text().splitlines():
        if raw.startswith(START_END):
            return strokes
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        cmd = line.split()[0]
        args = {k: float(v) for k, v in TOKEN.findall(line[len(cmd) :])}
        if cmd in ("M82", "M83"):
            relative_e = cmd == "M83"
        elif cmd in ("G90", "G91"):
            absolute_xyz = cmd == "G90"
        elif cmd == "G92":
            x, y, z, e = (args.get(k, v) for k, v in zip("XYZE", (x, y, z, e)))
        elif cmd in ("G0", "G1", "G2", "G3"):
            if cmd in ("G2", "G3") and "E" in args:
                raise ValueError("arc extrusion in the start G-code")
            nx, ny, nz = (
                args.get(k, v) if absolute_xyz else v + args.get(k, 0)
                for k, v in zip("XYZ", (x, y, z))
            )
            de = args.get("E", 0) if relative_e else args.get("E", e) - e
            e = e + args.get("E", 0) if relative_e else args.get("E", e)
            run = math.hypot(nx - x, ny - y)
            if de > 1e-7 and run > 1e-7 and nz < 1.0:
                wide = max(de * filament_area / run / max(nz, 0.1), 0.4)
                strokes.append(LineString([(x, y), (nx, ny)]).buffer(wide / 2))
            x, y, z = nx, ny, nz
    raise ValueError("no end of machine start G-code")


def start_clearance(path, paths, filament_area):
    """Air between the first layer's beads and the load line's, negative overlap as 0."""
    strokes = start_strokes(path, filament_area)
    if not strokes:
        raise ValueError("no load line in the start G-code")
    line = unary_union(strokes)
    first = unary_union([p.buffer(w / 2, quad_segs=3) for p, w, _ in paths])
    machine = json.loads((Path(__file__).parent / "print/machine.json").read_text())
    offset = [float(v) for v in machine["extruder_offset"][0].split("x")]
    corner = Polygon([tuple(map(float, p.split("x"))) for p in machine["bed_exclude_area"]])
    return {
        "excluded_corner_clearance_mm": round(
            first.distance(translate(corner, xoff=-offset[0], yoff=-offset[1])), 3
        ),
        "load_line_bounds_mm": [round(v, 3) for v in line.bounds],
        "first_layer_bounds_mm": [round(v, 3) for v in first.bounds],
        "bead_clearance_mm": round(first.distance(line), 3),
        "overlap_mm2": round(first.intersection(line).area, 3),
    }


def filament_area():
    profile = json.loads((Path(__file__).parent / "print/filament.json").read_text())
    return math.pi * float(profile["filament_diameter"][0]) ** 2 / 4


class ReleaseInterface:
    """One part's declared air gaps, checked layer by layer against sections and actual beads."""

    def __init__(self, policy, xoff, yoff, gcode, area):
        self.policy = policy
        self.zones = [translate(box(*z), xoff, yoff) for z in policy["zones"]]
        self.air = policy["air_layers"] * policy["layer_height"]
        self.top = policy["ceiling_z"] - self.air
        self.first_ceiling = policy["ceiling_z"] + policy["layer_height"]
        self.gcode = gcode
        self.area = area
        self.catch = Polygon()
        self.catches = [0.0] * len(self.zones)
        self.failures = []
        self.wall_gap = self.bead_gap = self.bead_clearance = math.inf
        self.occupied = 0.0
        self.air_layers_seen = 0
        self.start = None

    def fail(self, z, why):
        self.failures.append(
            {"z": z, "feature": "release interface", "why": why, "unsupported_mm": None}
        )

    def plugs(self, section):
        """Per zone, the solids wholly inside it. A plug joined to the deck is not among them."""
        return [unary_union([g for g in self.solids(section) if zone.covers(g)]) for zone in self.zones]

    @staticmethod
    def solids(section):
        return list(getattr(section, "geoms", [section]))

    def below(self, z, section, paths):
        for plug, zone in zip(self.plugs(section), self.zones):
            if plug.is_empty:
                continue
            deck = unary_union([g for g in self.solids(section) if not zone.covers(g)])
            gap = plug.distance(deck)
            self.wall_gap = min(self.wall_gap, gap)
            if gap < self.policy["min_wall_gap_mm"]:
                self.fail(z, f"plug {gap:.3f} mm from the deck")
            near = zone.buffer(3)
            inner, outer = [], []
            for line, width, _ in paths:
                if line.intersects(near):
                    bead = line.buffer(width / 2, quad_segs=3)
                    (inner if plug.buffer(TOL * 2).covers(line) else outer).append(bead)
            inner, outer = unary_union(inner), unary_union(outer)
            if inner.is_empty:
                self.fail(z, "plug has no toolpath")
            elif not outer.is_empty:
                gap = inner.distance(outer)
                self.bead_gap = min(self.bead_gap, gap)
                if gap < self.policy["min_bead_gap_mm"]:
                    self.fail(z, f"plug beads {gap:.3f} mm from deck beads")

    def layer(self, z, height, section, paths, flows):
        """Support the air gap adds to this layer's, empty outside the first ceiling layer."""
        if z == height and z < self.top + TOL:  # the first layer sits on the bed, by the load line
            self.start = start_clearance(self.gcode, paths, self.area)
            if self.start["bead_clearance_mm"] < self.policy["min_start_clearance_mm"]:
                self.fail(z, f"first layer {self.start['bead_clearance_mm']} mm from the load line")
        if z < self.top - TOL:
            self.below(z, section, paths)
            return Polygon()
        if abs(z - self.top) <= TOL:
            self.below(z, section, paths)
            plugs = self.plugs(section)
            self.catch = unary_union(plugs)
            self.catches = [round(p.area, 2) for p in plugs]
            return Polygon()
        if z < self.policy["ceiling_z"] + TOL:
            self.air_layers_seen += 1
            material = section.intersection(self.catch).area
            self.occupied = max(self.occupied, material)
            if material > 0.01:
                self.fail(z, f"{material:.2f} mm2 of solid in the air gap over the plug")
            return Polygon()
        if abs(z - self.first_ceiling) > TOL:
            return Polygon()
        if abs(height - self.policy["layer_height"]) > TOL:
            self.fail(z, f"first ceiling layer {height:.3f} mm tall")
        if self.air_layers_seen != self.policy["air_layers"]:
            self.fail(z, f"{self.air_layers_seen} air layers, not {self.policy['air_layers']}")
        if not all(self.catches):
            self.fail(z, "a pocket has no separate plug under its ceiling")
        for (line, _, feature), flow in zip(paths, flows):
            if line.intersects(self.catch) and flow > 0:
                # A bead over air stays about round and hangs from the nozzle, here at z.
                hang = 2 * math.sqrt(flow * self.area / math.pi)
                clear = z - hang - self.top
                self.bead_clearance = min(self.bead_clearance, clear)
                if clear < self.policy["min_bead_clearance_mm"]:
                    self.fail(z, f"{feature} bead {clear:.3f} mm above the plug")
        return self.catch

    def report(self, extension_spans):
        if self.start is None:
            self.fail(None, "the first layer was not checked against the load line")
        finite = lambda v: round(v, 3) if math.isfinite(v) else None
        return {
            "extension": "plug_release_gap",
            "pass": not self.failures,
            "failures": self.failures[:40],
            "ceiling_z": self.policy["ceiling_z"],
            "plug_top_z": round(self.top, 3),
            "air_layers": self.air_layers_seen,
            "air_mm": round(self.air, 3),
            "solid_in_air_mm2": round(self.occupied, 3),
            "plug_top_area_mm2": self.catches,
            "min_wall_gap_mm": finite(self.wall_gap),
            "min_bead_gap_mm": finite(self.bead_gap),
            "min_ceiling_bead_clearance_mm": finite(self.bead_clearance),
            "spans_over_plug": extension_spans,
            "load_line": self.start,
        }


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
    bbox = plates[0]["objects"][0]["bbox"]
    section = sectioner(stl, bbox, offset)
    policy = RELEASE_INTERFACES.get(Path(stl).stem)
    release = (
        ReleaseInterface(policy, bbox["x"] - offset[0], bbox["y"] - offset[1], path, filament_area())
        if policy
        else None
    )
    release_spans = 0
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
        middle = z - height / 2
        current = section(middle + 0.00001)
        inside = current.buffer(TOL * 2)
        either_side = None
        if not bed.buffer(TOL).covers(current) or z > float(machine["printable_height"]):
            raise ValueError(f"layer {n} conflicts with printer volume/excluded corner")
        # Structural solid from the preceding CAD slice, not a filled projection of
        # the whole object. This preserves designed infill cavities but never treats
        # a vent/window outside that slice as material. Cross-check actual toolpaths
        # against the placed section so a stale/rotated/different job cannot use it.
        support = previous.buffer(height + TOL, quad_segs=3)
        catch = release.layer(z, height, current, paths, layer["flows"]) if release else Polygon()
        if not catch.is_empty:
            # the same overlap a bead may have over the edge of the section under it
            support = support.union(catch.buffer(height + TOL, quad_segs=3))
        accepted = []
        for line, width, feature in paths:
            if not inside.covers(line):
                # A horizontal CAD face exactly on the slicer's mid-layer sampling plane may be
                # kept from either side (a nut slot floor at 12.9 mm in a 12.8-13.0 mm layer).
                # Such a path may fit just below the plane; support still uses only `current`.
                if either_side is None:
                    either_side = current.union(section(middle - 0.00001)).buffer(TOL * 2)
                if not either_side.covers(line):
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
                    release_spans += not catch.is_empty
                else:
                    failures.append(item)
            if len(failures) == failures_before:
                accepted.append(line.buffer(width / 2, quad_segs=3))
        previous = current
        previous_z = z
    if not checked:
        raise ValueError("no deposition layers")
    interface = release.report(release_spans) if release else None
    return {
        "policy_version": RELEASE_VERSION if release else VERSION,
        "pass": not failures and (interface is None or interface["pass"]),
        "layers_checked": checked,
        "max_bridge_mm": MAX_BRIDGE,
        "failures": failures + (interface["failures"] if interface else []),
        "bridges": bridges,
        **({"release_interface": interface} if interface else {}),
    }


def report_load_line(gcode, out):
    """The first layer's clearance from the load line for any job, without judging it."""
    first = next(iter(layers(gcode)))
    result = start_clearance(gcode, first["paths"], filament_area())
    Path(out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    if sys.argv[1] == "--load-line":
        report_load_line(sys.argv[2], sys.argv[3])
        sys.exit(0)
    try:
        result = check(sys.argv[1], sys.argv[2], sys.argv[3])
    except Exception as error:
        version = RELEASE_VERSION if Path(sys.argv[2]).stem in RELEASE_INTERFACES else VERSION
        result = {"policy_version": version, "pass": False, "error": str(error)}
    Path(sys.argv[4]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("failures", "bridges")}))
    sys.exit(0 if result["pass"] else 1)
