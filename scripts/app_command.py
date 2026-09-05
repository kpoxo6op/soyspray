"""Run a maintained app Makefile without adding a second application inventory."""

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(app, action, python, revision, root=ROOT):
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", app):
        raise ValueError("APP must be an Application name.")
    makefile = root / "apps" / app / "Makefile"
    if not makefile.is_file() or not makefile.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"{app} has no maintained operation file at apps/{app}/Makefile.")
    return [
        "make",
        "--no-print-directory",
        "-f",
        str(makefile),
        action,
        f"PYTHON={python}",
        f"REVISION={revision}",
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "diff", "deploy", "smoke", "restore-check"))
    parser.add_argument("--app", required=True)
    parser.add_argument("--python", default="soyspray-venv/bin/python")
    parser.add_argument("--revision", default="HEAD")
    args = parser.parse_args()
    try:
        argv = command(args.app, args.action, args.python, args.revision)
    except ValueError as error:
        parser.exit(2, f"unknown: {error}\n")
    os.chdir(ROOT)
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
