#!/usr/bin/env python3
"""Parse repository YAML files without requiring a cluster."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_ROOTS = [
    ".github",
    "apis",
    "kubernetes",
    "playbooks/argocd/applications/kong-bank-lab",
    "platform",
    "tests",
]


def yaml_files() -> list[Path]:
    paths: list[Path] = []
    for root in YAML_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        paths.extend(path for path in base.rglob("*") if path.suffix in {".yaml", ".yml"})
    paths.append(ROOT / "mkdocs.yml")
    return sorted(set(paths))


def main() -> int:
    errors: list[str] = []
    for path in yaml_files():
        try:
            list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    if errors:
        print("YAML validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"YAML validation passed for {len(yaml_files())} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
