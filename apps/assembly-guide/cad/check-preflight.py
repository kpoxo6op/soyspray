"""Exercise real CAD rendering, Bambu slicing and artifact admission; never contact a printer.

Usage: python3 check-preflight.py ~/prints/new-preflight-check
Requires the same dependencies and Flatpak access as preflight.mjs, plus Git history
containing b0584b1c (the original unsupported shelf regression).
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
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


try:
    good = root / "fixed-shelves"
    rc, d = run(cad, good, ["drive_tray", "switch_shelf"])
    record(
        "fixed source through real renderer and slicer",
        rc == 0 and d["pass"] and all(not v["problems"] for v in d["parts"].values()),
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
        ["git", "add", "preflight.mjs", "check-support.py", "check-support.py.lock", "print"],
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
        "source and committed STL disagreement is blocked",
        rc == 1
        and not d["pass"]
        and any("differs from the commit" in x for x in d["parts"]["drive_tray"]["problems"])
        and not list((root / "stale-input").rglob("*.gcode.3mf")),
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
