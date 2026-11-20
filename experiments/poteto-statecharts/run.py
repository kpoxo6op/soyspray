#!/usr/bin/env python3
"""Rerun the six bounded experiments and current-code replays outside the repo."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RUNS = [
    ("intake-normal", "IntakeRecovery", "intake", 0),
    ("intake-crash", "IntakeRecovery", "intake", 1),
    ("stale-guarded", "StaleOperation", "stale", 0),
    ("stale-mutant", "StaleOperation", "stale", 1),
    ("promotion-current", "ImagePromotion", "promotion", 0),
    ("promotion-mutant", "ImagePromotion", "promotion", 1),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--tlc", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[1]
    pins = json.loads((here / "provenance.json").read_text())
    head = subprocess.check_output(
        ["git", "-C", str(args.upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != pins["pstack_commit"] or sha(args.tlc) != pins["tlc_sha256"]:
        parser.error(
            "Tool provenance differs; review the new tools before updating provenance.json"
        )
    for name, expected in pins["source_sha256"].items():
        if sha(repo / name) != expected:
            parser.error(
                f"Covered source changed: {name}. Reconcile its model before moving the coverage record."
            )
    args.out.mkdir(parents=True, exist_ok=False)
    env = dict(
        os.environ,
        TLA2TOOLS=str(args.tlc.resolve()),
        JAVA=str(args.java.resolve()),
        JAVA_TOOL_OPTIONS="-Xmx512m",
    )
    script = args.upstream.resolve() / "pstack/skills/statechart/scripts/statechart"
    summary = []
    with tempfile.TemporaryDirectory(prefix="soyspray-statecharts-") as scratch:
        models = Path(scratch) / "models"
        shutil.copytree(here / "models", models)
        for name, model, view, expected in RUNS:
            started = time.monotonic()
            command = [
                str(script),
                str(models / f"{model}.tla"),
                "--config",
                str(models / f"{name}.cfg"),
                "--view",
                str(models / f"{view}.view.mjs"),
                "--out",
                str(args.out.resolve() / name),
            ]
            result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=90)
            if result.returncode != expected:
                sys.stderr.write(result.stdout + result.stderr)
                raise RuntimeError(f"{name}: expected {expected}, got {result.returncode}")
            report = (args.out / name / "report.md").read_text()
            if "NoDeadlock" not in report.split("## Rules that hold")[-1]:
                raise RuntimeError(f"{name}: unexpected deadlock")
            counts = re.search(r"TLC reached (\d+) states and (\d+) steps", report)
            record = {
                "name": name,
                "exit": result.returncode,
                "expected": expected,
                "seconds": round(time.monotonic() - started, 2),
                "states": int(counts[1]),
                "steps": int(counts[2]),
            }
            summary.append(record)
            print(json.dumps(record), flush=True)
    replay = subprocess.check_output(
        [sys.executable, str(here / "replay.py"), str(repo)], text=True, timeout=60
    )
    json.loads(replay)
    (args.out / "replay.json").write_text(replay)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "Expected outcomes reproduced. Three failing models are intentional findings/controls, not safety passes."
    )


if __name__ == "__main__":
    main()
