#!/usr/bin/env python3
"""Run explicit cluster smoke checks for goal-001."""

from __future__ import annotations

import subprocess
import sys


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.returncode, result.stdout.strip()


def main() -> int:
    checks = [
        ("current context", ["kubectl", "config", "current-context"]),
        ("server version", ["kubectl", "version"]),
        ("readyz", ["kubectl", "get", "--raw=/readyz"]),
    ]
    failed = False
    for label, command in checks:
        code, output = run(command)
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if output:
            print(output.splitlines()[0])
        if code != 0:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

