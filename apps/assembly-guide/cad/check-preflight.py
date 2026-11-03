"""Exercise real CAD rendering, Bambu slicing and artifact admission; never contact a printer.

Usage: python3 check-preflight.py ~/prints/new-preflight-check
Requires the same dependencies and Flatpak access as preflight.mjs, plus Git history
containing b0584b1c (the original unsupported shelf regression).
"""

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
from collections import Counter

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
            for dx in (-0.01, 0, 0.01) for dy in (-0.01, 0, 0.01) for dz in (-0.01, 0, 0.01)
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
    """For each model layer, which bed footprints receive extruded filament."""
    layers, x, y, relative = [], 0.0, 0.0, False
    for raw in gcode.read_text().splitlines():
        if raw == "; MACHINE_END_GCODE_START":
            break
        if raw.startswith("; CHANGE_LAYER"):
            layers.append(set())
        words = dict(re.findall(r" ([XYE])(-?[\d.]+)", raw.split(";", 1)[0]))
        relative = raw.startswith("M83") or (relative and not raw.startswith("M82"))
        if re.match(r"G[0-3] ", raw):
            x, y = float(words.get("X", x)), float(words.get("Y", y))
            if layers and relative and float(words.get("E", 0)) > 0:
                layers[-1].update(
                    i for i, (lo, hi) in enumerate(footprints)
                    if lo[0] - 1 <= x <= hi[0] + 1 and lo[1] - 1 <= y <= hi[1] + 1
                )
    return layers


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
    batch = root / "remaining-posts"
    rc, d = run(cad, batch, ["lower_posts_remaining"])
    entry = d["parts"]["lower_posts_remaining"]
    stl = batch / "stl/lower_posts_remaining.stl"
    refs = root / "fresh-posts"
    subprocess.run(
        ["node", "render.mjs", "--output-dir", str(refs), "post_lower_a", "post_lower_b"],
        cwd=cad,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    reference = {p: triangles(refs / "stl" / (p + ".stl")) for p in ("post_lower_a", "post_lower_b")}
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
    box = json.loads((batch / "lower_posts_remaining/result.json").read_text())["sliced_plates"][0][
        "objects"
    ][0]["bbox"]
    machine = json.loads((cad / "print/machine.json").read_text())
    offset = [float(v) for v in machine["extruder_offset"][0].split("x")]
    low = [min(p[1][a] for p in pieces) for a in (0, 1)]
    shift = [(box["x"], box["y"])[a] - low[a] - offset[a] for a in (0, 1)]
    footprints = [
        ([lo[a] + shift[a] for a in (0, 1)], [hi[a] + shift[a] for a in (0, 1)])
        for _, lo, hi in pieces
    ]
    printed = layers_printing(batch / "lower_posts_remaining/plate_1.gcode", footprints)
    job = batch / "lower_posts_remaining/lower_posts_remaining.gcode.3mf"
    record(
        "remaining lower posts are one current A and two current B, each printed on every checked layer",
        rc == 0
        and d["pass"]
        and not entry["problems"]
        and entry["geometry"]["pass"] is True
        and entry["stl"] == sha(stl)
        and sha(job) == entry["job"]
        and sorted(names) == ["post_lower_a", "post_lower_b", "post_lower_b"]
        and min(gaps) > 0
        and len(printed) == entry["geometry"]["layers_checked"]
        and all(layer == set(range(len(pieces))) for layer in printed),
        parts=names,
        clearance_mm=round(min(gaps), 3),
        layers=len(printed),
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
    overlapping = layout.replace("{ part: 'post_lower_b', at: [0, 30] }", "{ part: 'post_lower_b', at: [0, 10] }")
    assert overlapping != layout
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
