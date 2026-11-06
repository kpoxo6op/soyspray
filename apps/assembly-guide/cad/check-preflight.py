"""Exercise real CAD rendering, Bambu slicing and artifact admission; never contact a printer.

Usage: python3 check-preflight.py ~/prints/new-preflight-check
Requires the same dependencies and Flatpak access as preflight.mjs, plus Git history
containing b0584b1c (the original unsupported shelf regression), 4bf33ded, a1d5e6bc and
b843191d (the fused pocket lattice). The flat mid deck and power base comparisons run
check-flat-deck.py and check-base-tub.py through uv.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile

cad = Path(__file__).resolve().parent
repo = Path(
    subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=cad, text=True).strip()
)
if len(sys.argv) != 2:
    raise SystemExit("usage: python3 check-preflight.py <new-output-directory>")
root = Path(sys.argv[1]).expanduser().resolve()
root.mkdir(parents=True, exist_ok=False)
before = root / "before"
completed = False
results = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cwd, out, parts, extra=None):
    env = os.environ.copy()
    env.update(extra or {})
    r = subprocess.run(
        ["node", "preflight.mjs", str(out), *parts],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    (root / (out.name + ".log")).write_text(r.stdout + r.stderr)
    report = (
        json.loads((out / "preflight.json").read_text())
        if (out / "preflight.json").exists()
        else None
    )
    print(out.name, r.returncode, r.stdout[-1400:], flush=True)
    return r.returncode, report


def record(name, condition, **evidence):
    results.append(dict(case=name, passed=bool(condition), **evidence))
    assert condition, (name, evidence)


def triangles(stl):
    b = stl.read_bytes()
    n = struct.unpack_from("<I", b, 80)[0]
    assert len(b) == 84 + 50 * n, stl
    return [
        tuple(struct.unpack_from("<3f", b, 84 + 50 * i + 12 + 12 * k) for k in range(3))
        for i in range(n)
    ]


def canonical(t):
    k = t.index(min(t))
    return t[k:] + t[:k]


def islands(tris):
    """Split a mesh into separately standing pieces: connected shells, merged when nested."""
    parent = list(range(len(tris)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, t in enumerate(tris):
        for v in t:
            parent[find(i)] = find(seen.setdefault(v, i))
    groups = {}
    for i in range(len(tris)):
        groups.setdefault(find(i), []).append(tris[i])
    boxes = []
    for g in groups.values():
        lo = [min(v[a] for t in g for v in t) for a in range(3)]
        hi = [max(v[a] for t in g for v in t) for a in range(3)]
        for other in [b for b in boxes if all(lo[a] < b[2][a] and b[1][a] < hi[a] for a in (0, 1))]:
            boxes.remove(other)
            g = g + other[0]
            lo = [min(lo[a], other[1][a]) for a in range(3)]
            hi = [max(hi[a], other[2][a]) for a in range(3)]
        boxes.append((g, lo, hi))
    return sorted(boxes, key=lambda b: (b[1][1], b[1][0]))


def same_part(piece, low, reference):
    """True when piece, moved to its lowest corner, is the reference mesh without any
    rotation, mirroring or scaling. Matching tolerates float32 rounding of the move."""
    if len(piece) != len(reference):
        return False
    grid = {}
    ids = {}
    for t in reference:
        for v in t:
            if v not in ids:
                ids[v] = len(ids)
                grid.setdefault(tuple(round(c, 2) for c in v), []).append(v)

    def match(v):
        p = [v[a] - low[a] for a in range(3)]
        cells = [
            (round(p[0], 2) + dx, round(p[1], 2) + dy, round(p[2], 2) + dz)
            for dx in (-0.01, 0, 0.01)
            for dy in (-0.01, 0, 0.01)
            for dz in (-0.01, 0, 0.01)
        ]
        for cell in cells:
            for r in grid.get(tuple(round(c, 2) for c in cell), ()):
                if max(abs(r[a] - p[a]) for a in range(3)) < 1e-4:
                    return ids[r]
        return None

    def canonical(t):
        k = t.index(min(t))
        return t[k:] + t[:k]

    want = Counter(canonical(tuple(ids[v] for v in t)) for t in reference)
    got = Counter()
    for t in piece:
        m = tuple(match(v) for v in t)
        if None in m:
            return False
        got[canonical(m)] += 1
    return got == want


def layers_printing(gcode, footprints):
    """For each model layer, its height and which bed footprints receive extruded filament."""
    layers, x, y, relative = [], 0.0, 0.0, False
    for raw in gcode.read_text().splitlines():
        if raw == "; MACHINE_END_GCODE_START":
            break
        if raw.startswith("; CHANGE_LAYER"):
            layers.append((None, set()))
        elif raw.startswith("; Z_HEIGHT:") and layers:
            layers[-1] = (float(raw.split(":", 1)[1]), layers[-1][1])
        words = dict(re.findall(r" ([XYE])(-?[\d.]+)", raw.split(";", 1)[0]))
        relative = raw.startswith("M83") or (relative and not raw.startswith("M82"))
        if re.match(r"G[0-3] ", raw):
            x, y = float(words.get("X", x)), float(words.get("Y", y))
            if layers and relative and float(words.get("E", 0)) > 0:
                layers[-1][1].update(
                    i
                    for i, (lo, hi) in enumerate(footprints)
                    if lo[0] - 1 <= x <= hi[0] + 1 and lo[1] - 1 <= y <= hi[1] + 1
                )
    return layers


def check_batch(name, expected):
    """Prepare a renderer batch preset and prove its exact fresh composition and printing."""
    batch = root / name
    rc, d = run(cad, batch, [name])
    entry = d["parts"][name]
    stl = batch / "stl" / (name + ".stl")
    refs = root / (name + "-fresh-parts")
    subprocess.run(
        ["node", "render.mjs", "--output-dir", str(refs), *sorted(set(expected))],
        cwd=cad,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    reference = {p: triangles(refs / "stl" / (p + ".stl")) for p in set(expected)}
    pieces = islands(triangles(stl))
    names = [
        next((p for p, t in reference.items() if same_part(g, lo, t)), "unknown")
        for g, lo, _ in pieces
    ]
    gaps = [
        max(b[1][0] - a[2][0], a[1][0] - b[2][0], b[1][1] - a[2][1], a[1][1] - b[2][1])
        for i, a in enumerate(pieces)
        for b in pieces[i + 1 :]
    ]
    box = json.loads((batch / name / "result.json").read_text())["sliced_plates"][0]["objects"][0][
        "bbox"
    ]
    machine = json.loads((cad / "print/machine.json").read_text())
    offset = [float(v) for v in machine["extruder_offset"][0].split("x")]
    low = [min(p[1][a] for p in pieces) for a in (0, 1)]
    shift = [(box["x"], box["y"])[a] - low[a] - offset[a] for a in (0, 1)]
    footprints = [
        ([lo[a] + shift[a] for a in (0, 1)], [hi[a] + shift[a] for a in (0, 1)])
        for _, lo, hi in pieces
    ]
    printed = layers_printing(batch / name / "plate_1.gcode", footprints)
    # Each part receives filament on every layer up to its own top, and on none above it.
    tops = [hi[2] for _, _, hi in pieces]
    wanted = [{i for i, top in enumerate(tops) if z <= top + 0.01} for z, _ in printed]
    job = batch / name / (name + ".gcode.3mf")
    record(
        f"{name} is exactly {', '.join(sorted(expected))} from fresh source,"
        " each printed on every layer up to its own height",
        rc == 0
        and d["pass"]
        and not entry["problems"]
        and entry["geometry"]["pass"] is True
        and entry["stl"] == sha(stl)
        and sha(job) == entry["job"]
        and sorted(names) == sorted(expected)
        and min(gaps) >= 9.99
        and len(printed) == entry["geometry"]["layers_checked"]
        and all(z is not None for z, _ in printed)
        and all(got == want for (_, got), want in zip(printed, wanted)),
        parts=names,
        layers_per_part=[sum(i in got for _, got in printed) for i in range(len(pieces))],
        clearance_mm=round(min(gaps), 3),
        bed_bbox=box,
        layers=len(printed),
        minutes=entry["minutes"],
        grams=entry["grams"],
        sha256=entry.get("job"),
    )
    return batch / name, stl


try:
    good = root / "fixed-shelves"
    rc, d = run(cad, good, ["drive_tray", "switch_shelf"])
    record(
        "fixed source through real renderer and slicer",
        rc == 0
        and d["pass"]
        and set(d["parts"]) == {"drive_tray", "switch_shelf"}
        and all(not v["problems"] for v in d["parts"].values()),
        report=str(good / "preflight.json"),
    )
    for p, v in d["parts"].items():
        artifact = good / p / (p + ".gcode.3mf")
        with zipfile.ZipFile(artifact) as z:
            archived = z.read("Metadata/plate_1.gcode")
        record(
            p + " exported job matches report and inspected Gcode",
            sha(artifact) == v["job"] and archived == (good / p / "plate_1.gcode").read_bytes(),
            sha256=sha(artifact),
        )
    check_batch("lower_posts_remaining", ["post_lower_a", "post_lower_b", "post_lower_b"])
    upper, upper_stl = check_batch(
        "upper_posts_remaining", ["post_upper_a", "post_upper_a", "post_upper_b", "post_upper_b"]
    )
    # The checker in the pinned preparer (4bf33ded) sampled only above the slicer's mid-layer
    # plane, so the cap-nut slot floor on that plane failed this same job as "outside the model".
    pinned = root / "pinned-checker"
    for f in ("check-support.py", "check-support.py.lock", "print/machine.json"):
        (pinned / f).parent.mkdir(parents=True, exist_ok=True)
        (pinned / f).write_bytes(
            subprocess.check_output(
                ["git", "show", f"4bf33ded:apps/assembly-guide/cad/{f}"], cwd=repo
            )
        )
    old_geometry = root / "pinned-checker-geometry.json"
    subprocess.run(
        [
            os.environ.get("UV", "uv"),
            "run",
            "--locked",
            "--script",
            str(pinned / "check-support.py"),
            str(upper / "plate_1.gcode"),
            str(upper_stl),
            str(upper / "result.json"),
            str(old_geometry),
        ],
        stdout=subprocess.DEVNULL,
    )
    old = json.loads(old_geometry.read_text())
    record(
        "the pinned checker's mid-plane false failure is fixed on the same upper post job",
        old["pass"] is False
        and "toolpath outside placed model at layer 65" in old.get("error", ""),
        pinned_error=old.get("error"),
    )
    # The mid deck stands on its rear edge behind the mast; the mast stops at 140 mm.
    check_batch("mid_deck_and_mast", ["zigbee_mast", "mid_deck"])
    # The mid deck lying flat, a quarter turn in plan, with a plug in each underside post pocket.
    flat = root / "mid-deck-flat"
    flat_rc, flat_report = run(cad, flat, ["mid_deck_flat"])
    entry = flat_report["parts"]["mid_deck_flat"]
    flat_dir = flat / "mid_deck_flat"
    plate = json.loads((flat_dir / "result.json").read_text())["sliced_plates"][0]
    box = plate["objects"][0]["bbox"]
    record(
        "the flat mid deck prints lying flat with every layer supported",
        flat_rc == 0
        and flat_report["pass"]
        and not entry["problems"]
        and not plate.get("warning_message")
        and entry["geometry"]["pass"] is True
        and sha(flat_dir / "mid_deck_flat.gcode.3mf") == entry["job"]
        and [round(box[k], 2) for k in ("width", "depth", "height")] == [209, 245, 8],
        bed_bbox=box,
        layers=entry["geometry"]["layers_checked"],
        longest_bridge_mm=max(
            b["unsupported_mm"]
            for b in json.loads((flat_dir / "geometry.json").read_text())["bridges"]
        ),
        minutes=entry["minutes"],
        grams=entry["grams"],
        sha256=entry.get("job"),
    )
    # The one-pocket coupon for testing plug removal and post fit before a whole deck.
    coupon = root / "mid-deck-pocket-coupon"
    coupon_rc, coupon_report = run(cad, coupon, ["mid_deck_pocket_coupon"])
    entry = coupon_report["parts"]["mid_deck_pocket_coupon"]
    record(
        "the one-pocket coupon prints with every layer supported",
        coupon_rc == 0 and coupon_report["pass"] and not entry["problems"],
        minutes=entry["minutes"],
        grams=entry["grams"],
        sha256=entry.get("job"),
    )
    # Against the canonical mid deck on edge, section by section: the same solid above the seat
    # planes; below them nothing removed, material added only in the four underside pockets,
    # solid pocket walls round each seat outline and a plug inside it, with air between them in
    # the CAD and in the actual beads. The coupon is the deck's corner on every layer.
    refs = root / "mid-deck-flat-reference"
    subprocess.run(
        ["node", "render.mjs", "--output-dir", str(refs), "mid_deck"],
        cwd=cad,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    def compare_flat(job, out, *more):
        return subprocess.run(
            [os.environ.get("UV", "uv"), "run", "--script", str(cad / "check-flat-deck.py"),
             str(refs / "stl/mid_deck.stl"), str(job), str(root / out), *map(str, more)],
            capture_output=True,
            text=True,
        ).returncode, json.loads((root / out).read_text())

    compared, sections = compare_flat(flat, "mid-deck-flat-sections.json", coupon)
    record(
        "the flat mid deck is the canonical deck plus separate plugs, and the coupon is its corner",
        compared == 0 and sections["pass"] is True,
        **{k: v for k, v in sections.items() if k not in ("layers", "beads")},
        report=str(root / "mid-deck-flat-sections.json"),
    )
    # The top cap prints upside down. Two stepped layers now close each socket-head seat
    # onto its screw hole instead of a ring of wall over air.
    cap = root / "top-cap"
    cap_rc, cap_report = run(cad, cap, ["top_cap"])
    entry = cap_report["parts"]["top_cap"]
    seat_bridges = [
        b
        for b in json.loads((cap / "top_cap/geometry.json").read_text())["bridges"]
        if 4.5 <= b["z"] <= 5.1
    ]
    record(
        "top cap prints with every head seat layer bridged end to end",
        cap_rc == 0
        and cap_report["pass"]
        and not entry["problems"]
        and entry["geometry"]["pass"] is True
        and sha(cap / "top_cap/top_cap.gcode.3mf") == entry["job"]
        and seat_bridges
        and all(
            b["end_anchors"] and b["spans_gap"] and b["unsupported_mm"] <= 6.7 for b in seat_bridges
        ),
        seat_bridges=len(seat_bridges),
        longest_seat_bridge_mm=max((b["unsupported_mm"] for b in seat_bridges), default=None),
        minutes=entry["minutes"],
        grams=entry["grams"],
        sha256=entry.get("job"),
    )
    old_report = sha(good / "preflight.json")
    old_jobs = {p: sha(good / p / (p + ".gcode.3mf")) for p in d["parts"]}
    rc, _ = run(cad, good, ["drive_tray"])
    record(
        "existing run is rejected without overwriting evidence",
        rc == 2
        and sha(good / "preflight.json") == old_report
        and all(sha(good / p / (p + ".gcode.3mf")) == h for p, h in old_jobs.items()),
    )
    rc, d = run(
        cad,
        root / "renderer-failure",
        ["drive_tray"],
        {"FONT_TTF": "/definitely-missing-soyrack-font.ttf"},
    )
    record(
        "real renderer failure remains failed",
        rc != 0
        and d["pass"] is False
        and "render failed" in d["error"]
        and not list((root / "renderer-failure").rglob("*.gcode.3mf")),
    )
    rc, d = run(
        cad,
        root / "slicer-unavailable",
        ["drive_tray"],
        {"BAMBU_STUDIO": "/definitely-missing-bambu-studio"},
    )
    record(
        "unavailable slicer remains failed",
        rc != 0
        and d["pass"] is False
        and not list((root / "slicer-unavailable").rglob("*.gcode.3mf")),
    )
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(before), "b0584b1c"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    oldcad = before / "apps/assembly-guide/cad"
    for filename in ("preflight.mjs", "render.mjs", "check-support.py", "check-support.py.lock"):
        shutil.copy2(cad / filename, oldcad / filename)
    shutil.copytree(cad / "print", oldcad / "print")
    (oldcad / "node_modules").symlink_to(cad / "node_modules", target_is_directory=True)
    subprocess.run(
        [
            "git",
            "add",
            "preflight.mjs",
            "render.mjs",
            "check-support.py",
            "check-support.py.lock",
            "print",
        ],
        cwd=oldcad,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-qm", "E2E: apply current admission tools to historical CAD"],
        cwd=oldcad,
        check=True,
    )
    rc, d = run(oldcad, root / "old-unsupported", ["drive_tray", "switch_shelf"])
    record(
        "original unsupported shelves are blocked",
        rc == 1
        and not d["pass"]
        and set(d["parts"]) == {"drive_tray", "switch_shelf"}
        and all(any("floating cantilever" in x for x in v["problems"]) for v in d["parts"].values())
        and not list((root / "old-unsupported").rglob("*.gcode.3mf")),
        problems={k: v["problems"] for k, v in d["parts"].items()},
    )
    rc, d = run(oldcad, root / "floating-island", ["coupon_keystone"])
    record(
        "a model half above the bed is blocked",
        rc == 1
        and not d["pass"]
        and d["parts"]["coupon_keystone"].get("geometry", {}).get("pass") is False,
    )
    rc, d = run(oldcad, root / "excluded-corner", ["base_tub"])
    record(
        "a model inside nominal dimensions but crossing the excluded corner is blocked",
        rc == 1 and not d["pass"],
    )
    subprocess.run(
        ["git", "restore", "--source=ff21c452", "--", "soyrack.scad", "stl"], cwd=oldcad, check=True
    )
    subprocess.run(["git", "add", "soyrack.scad", "stl"], cwd=oldcad, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "E2E: previous rounded-window shelves"], cwd=oldcad, check=True
    )
    rc, d = run(oldcad, root / "warning-free-bridge", ["drive_tray"])
    slice_result = json.loads((root / "warning-free-bridge/drive_tray/result.json").read_text())
    record(
        "warning-free long bridges are independently blocked",
        rc == 1
        and not d["pass"]
        and not slice_result["sliced_plates"][0].get("warning_message")
        and d["parts"]["drive_tray"]["geometry"]["pass"] is False
        and d["parts"]["drive_tray"]["geometry"]["failures_count"] > 0,
    )
    shutil.copy2(cad / "soyrack.scad", oldcad / "soyrack.scad")
    rc, d = run(oldcad, root / "stale-input", ["drive_tray"])
    record(
        "uncommitted manufacturing source is blocked",
        rc == 1
        and not d["pass"]
        and "uncommitted manufacturing inputs" in d.get("error", "")
        and not list((root / "stale-input").rglob("*.gcode.3mf")),
    )
    subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "E2E: fixed source with obsolete cached exports"],
        cwd=oldcad,
        check=True,
    )
    # A cached export is not an input: even a damaged one must never be sliced.
    (oldcad / "stl/drive_tray.stl").write_bytes(b"obsolete damaged cached mesh")
    rc, d = run(oldcad, root / "cached-stl-ignored", ["drive_tray"])
    fresh = root / "cached-stl-ignored/stl/drive_tray.stl"
    record(
        "obsolete cached STL cannot enter a prepared print",
        rc == 0
        and d["pass"]
        and set(d["parts"]) == {"drive_tray"}
        and d["parts"]["drive_tray"]["geometry"]["pass"] is True
        and d["parts"]["drive_tray"]["stl"] == sha(fresh)
        and fresh.stat().st_size > 84,
    )
    # A layout edit that puts posts on top of each other must stop before slicing.
    layout = (oldcad / "render.mjs").read_text()
    overlapping = layout.replace(
        "{ part: 'post_lower_b', at: [0, 30] }", "{ part: 'post_lower_b', at: [0, 10] }"
    ).replace("{ part: 'post_upper_b', at: [0, 90] }", "{ part: 'post_upper_b', at: [0, 75] }")
    assert overlapping.count("at: [0, 10]") == 1 and overlapping.count("at: [0, 75]") == 1
    (oldcad / "render.mjs").write_text(overlapping)
    subprocess.run(["git", "add", "render.mjs"], cwd=oldcad, check=True)
    subprocess.run(["git", "commit", "-qm", "E2E: overlapping post batch"], cwd=oldcad, check=True)
    rc, d = run(oldcad, root / "overlapping-batch", ["lower_posts_remaining"])
    record(
        "an overlapping post batch layout exports no job",
        rc == 1
        and not d["pass"]
        and "batch clearance" in d.get("error", "")
        and not list((root / "overlapping-batch").rglob("*.gcode.3mf")),
        error=d.get("error", "")[-300:],
    )
    rc, d = run(oldcad, root / "overlapping-upper-batch", ["upper_posts_remaining"])
    record(
        "an overlapping upper post batch layout exports no job",
        rc == 1
        and not d["pass"]
        and "batch clearance" in d.get("error", "")
        and not list((root / "overlapping-upper-batch").rglob("*.gcode.3mf")),
        error=d.get("error", "")[-300:],
    )
    # The cap as pinned (4bf33ded) left its head seats as ring ceilings over air.
    subprocess.run(
        ["git", "restore", "--source=4bf33ded", "--", "soyrack.scad"], cwd=oldcad, check=True
    )
    subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
    subprocess.run(["git", "commit", "-qm", "E2E: unstepped head seats"], cwd=oldcad, check=True)
    rc, d = run(oldcad, root / "unstepped-top-cap", ["top_cap"])
    seat_failures = [
        f
        for f in json.loads((root / "unstepped-top-cap/top_cap/geometry.json").read_text())[
            "failures"
        ]
        if f["layer"] == 23 and f["feature"] == "Overhang wall"
    ]
    record(
        "the unstepped top cap head seats are blocked",
        rc == 1
        and not d["pass"]
        and seat_failures
        and not list((root / "unstepped-top-cap").rglob("*.gcode.3mf")),
        failures=d["parts"]["top_cap"]["geometry"]["failures_count"],
    )
    # Only the seats changed: every differing triangle lies within the 8 mm head seats round
    # the four cap screw axes (x 12 and 241, y 20 and 189 in the rack, x 8 and 237 on the bed)
    # and below the pads' 10 mm. Seat walls keep r 4; new hole steps never come inside r 2.25.
    before_cap = Counter(
        canonical(t) for t in triangles(root / "unstepped-top-cap/stl/top_cap.stl")
    )
    after_cap = Counter(canonical(t) for t in triangles(cap / "stl/top_cap.stl"))
    removed, added = before_cap - after_cap, after_cap - before_cap
    axes = [(8, 20), (8, 189), (237, 20), (237, 189)]
    radius = lambda v: min(((v[0] - a) ** 2 + (v[1] - b) ** 2) ** 0.5 for a, b in axes)
    changed = [v for t in (removed + added).elements() for v in t]
    new = [v for t in added.elements() for v in t]
    record(
        "the stepped top cap differs from the old one only inside the four head seats",
        changed
        and all(radius(v) <= 4.05 and v[2] <= 10.01 for v in changed)
        and all(radius(v) >= 2.249 for v in new if 4.41 <= v[2] <= 4.81)
        and all(radius(v) >= 3.99 for v in new if v[2] < 4.39),
        changed_triangles=sum((removed + added).values()),
    )
    # The mid deck as it lay flat (a1d5e6bc) closed each underside post pocket in a ceiling over air.
    subprocess.run(
        ["git", "restore", "--source=a1d5e6bc", "--", "soyrack.scad"], cwd=oldcad, check=True
    )
    subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
    subprocess.run(["git", "commit", "-qm", "E2E: flat mid deck"], cwd=oldcad, check=True)
    rc, d = run(oldcad, root / "flat-mid-deck", ["mid_deck"])
    pocket_failures = [
        f
        for f in json.loads((root / "flat-mid-deck/mid_deck/geometry.json").read_text())["failures"]
        if abs(f["z"] - 3.2) < 0.01
    ]
    record(
        "the flat mid deck's post pocket ceilings stay blocked",
        rc == 1
        and not d["pass"]
        and pocket_failures
        and not list((root / "flat-mid-deck").rglob("*.gcode.3mf")),
        failures=d["parts"]["mid_deck"]["geometry"]["failures_count"],
    )
    # The current batch with the old mast foot (a1d5e6bc): flat 21 mm ceilings over its washers.
    current = (cad / "soyrack.scad").read_text()
    old = (oldcad / "soyrack.scad").read_text()
    module = lambda src: src[src.index("module zigbee_mast()") : src.index("// ---", src.index("module zigbee_mast()"))]
    (oldcad / "soyrack.scad").write_text(current.replace(module(current), module(old)))
    subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
    subprocess.run(["git", "commit", "-qm", "E2E: old mast foot"], cwd=oldcad, check=True)
    rc, d = run(oldcad, root / "old-mast-foot", ["mid_deck_and_mast"])
    geometry = json.loads((root / "old-mast-foot/mid_deck_and_mast/geometry.json").read_text())
    box = json.loads((root / "old-mast-foot/mid_deck_and_mast/result.json").read_text())[
        "sliced_plates"
    ][0]["objects"][0]["bbox"]
    # The mast is the first 84 mm of the batch in y; on the bed it starts at the object's y.
    in_mast = lambda f: max(f["from"][1], f["to"][1]) <= box["y"] + 84 + 1
    record(
        "the old mast foot's washer ceilings are blocked in the same batch",
        rc == 1
        and not d["pass"]
        and geometry.get("failures")
        and all(in_mast(f) and 6.1 <= f["z"] <= 6.5 for f in geometry["failures"])
        and not list((root / "old-mast-foot").rglob("*.gcode.3mf")),
        failures=len(geometry.get("failures", [])),
        bed_bbox=box,
    )
    # The same flat deck, straight pocket walls included, without plugs closes each pocket
    # ceiling over air again.
    plug = "module pocket_plug(k) {"
    assert current.count(plug) == 1
    (oldcad / "soyrack.scad").write_text(current.replace(plug, "module pocket_plug(k) {}\nmodule unused_plug(k) {"))
    subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
    subprocess.run(["git", "commit", "-qm", "E2E: flat deck without plugs"], cwd=oldcad, check=True)
    rc, d = run(oldcad, root / "flat-without-plugs", ["mid_deck_flat"])
    geometry = json.loads((root / "flat-without-plugs/mid_deck_flat/geometry.json").read_text())
    record(
        "the flat mid deck without its plugs is blocked at the pocket ceilings",
        rc == 1
        and not d["pass"]
        and geometry.get("failures")
        and all(abs(f["z"] - 3.2) < 0.01 for f in geometry["failures"])
        and not list((root / "flat-without-plugs").rglob("*.gcode.3mf")),
        failures=len(geometry.get("failures", [])),
    )
    # The lattice printed on 2026-11-06 (b843191d) passed every layer check and could not be
    # removed: a support PASS says nothing about removal. The release check refuses it.
    fused = subprocess.check_output(
        ["git", "show", "b843191d:apps/assembly-guide/cad/soyrack.scad"], cwd=repo, text=True
    )
    (oldcad / "soyrack.scad").write_text(fused)
    subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
    subprocess.run(["git", "commit", "-qm", "E2E: fused pocket lattice"], cwd=oldcad, check=True)
    rc, d = run(oldcad, root / "fused-lattice", ["mid_deck_flat"])
    compared, sections = compare_flat(root / "fused-lattice", "fused-lattice-sections.json")
    record(
        "the rejected fused lattice passes the support check and is refused by the release check",
        rc == 0
        and d["pass"]
        and compared == 1
        and sections["pass"] is False
        and sections["min_bead_gap_mm"] == 0
        and sections["crossing_paths"] > 0,
        min_bead_gap_mm=sections["min_bead_gap_mm"],
        crossing_paths=sections["crossing_paths"],
        plug_contact_cad_mm2=sections["plug_contact_cad_mm2"],
    )
    # The power base: every layer, the corner relief, and the tub it replaces in the rack.
    tub = root / "base-tub"
    tub_rc, tub_report = run(cad, tub, ["base_tub"])
    entry = tub_report["parts"]["base_tub"]
    tub_dir = tub / "base_tub"
    plate = json.loads((tub_dir / "result.json").read_text())["sliced_plates"][0]
    box = plate["objects"][0]["bbox"]
    record(
        "the power base prints on the bed with every layer supported",
        tub_rc == 0
        and tub_report["pass"]
        and not entry["problems"]
        and not plate.get("warning_message")
        and entry["geometry"]["pass"] is True
        and entry["geometry"]["layers_checked"] == 480
        and entry["geometry"]["failures_count"] == 0
        and sha(tub_dir / "base_tub.gcode.3mf") == entry["job"]
        and [round(box[k], 2) for k in ("width", "depth", "height")] == [240, 245, 96],
        bed_bbox=box,
        layers=entry["geometry"]["layers_checked"],
        longest_bridge_mm=max(
            b["unsupported_mm"] for b in json.loads((tub_dir / "geometry.json").read_text())["bridges"]
        ),
        wall_over_air=entry["watch"],
        minutes=entry["minutes"],
        grams=entry["grams"],
        sha256=entry.get("job"),
    )
    subprocess.run(["git", "restore", "--source=8210db5b", "--", "soyrack.scad"], cwd=oldcad, check=True)
    tub_refs = root / "base-tub-reference"
    subprocess.run(
        ["node", "render.mjs", "--output-dir", str(tub_refs), "base_tub"],
        cwd=oldcad,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    compared = subprocess.run(
        [os.environ.get("UV", "uv"), "run", "--script", str(cad / "check-base-tub.py"),
         str(tub_refs / "stl/base_tub.stl"), str(tub), str(root / "base-tub-sections.json")],
        capture_output=True,
        text=True,
    )
    sections = json.loads((root / "base-tub-sections.json").read_text())
    record(
        "the power base is the old tub less the corner relief, moved strap slots and hole steps",
        compared.returncode == 0 and sections["pass"] is True,
        removed_mm3=sections["removed_mm3"],
        nut_seats=sections["nut_seats"][0],
        first_layer=sections["first_layer"],
        report=str(root / "base-tub-sections.json"),
    )
    # Take each change back in the current tub: the same preparer must refuse it.
    undo = {
        "tub-without-relief": ("    if (!web) tub_relief();\n", ""),
        "tub-strap-slots-under-fins": ("[[19.5, 76], [143.5, 76]]", "[[21, 76], [143, 76]]"),
        "tub-ring-ceilings": ("      if (!web) translate([-M4_D / 2, 0, BASE_NUT_Z + NUT4[1]]) {", "      if (false) translate([-M4_D / 2, 0, BASE_NUT_Z + NUT4[1]]) {"),
    }
    outcome = {}
    for name, (new, old) in undo.items():
        assert current.count(new) == 1, name
        (oldcad / "soyrack.scad").write_text(current.replace(new, old))
        subprocess.run(["git", "add", "soyrack.scad"], cwd=oldcad, check=True)
        subprocess.run(["git", "commit", "-qm", f"E2E: {name}"], cwd=oldcad, check=True)
        rc, d = run(oldcad, root / name, ["base_tub"])
        geometry = d["parts"]["base_tub"].get("geometry", {})
        outcome[name] = dict(
            rc=rc,
            problems=d["parts"]["base_tub"]["problems"],
            failing_z=sorted({f["z"] for f in geometry.get("failures", [])}),
            jobs=[str(p) for p in (root / name).rglob("*.gcode.3mf")],
        )
    record(
        "without its relief the turned tub cannot be arranged and exports no job",
        outcome["tub-without-relief"]["rc"] == 1
        and "failed" in outcome["tub-without-relief"]["problems"][0]
        and not outcome["tub-without-relief"]["jobs"],
        evidence=outcome["tub-without-relief"],
    )
    record(
        "strap slots under the comb fins are blocked at those fins",
        outcome["tub-strap-slots-under-fins"]["rc"] == 1
        and outcome["tub-strap-slots-under-fins"]["failing_z"] == [3.6]
        and not outcome["tub-strap-slots-under-fins"]["jobs"],
        evidence=outcome["tub-strap-slots-under-fins"],
    )
    record(
        "nut slot ceilings closing as rings round the screw holes are blocked at the seat",
        outcome["tub-ring-ceilings"]["rc"] == 1
        and outcome["tub-ring-ceilings"]["failing_z"] == [90.2]
        and not outcome["tub-ring-ceilings"]["jobs"],
        evidence=outcome["tub-ring-ceilings"],
    )
    completed = True
finally:
    if before.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(before)], cwd=repo, check=True)
    result = {
        "cases": results,
        "all_passed": completed and all(x["passed"] for x in results),
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
    }
    (root / "e2e-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
