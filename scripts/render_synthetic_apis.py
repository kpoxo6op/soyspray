#!/usr/bin/env python3
"""Render goal-003 synthetic API manifests without applying them."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.synthetic_bank_config import ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import ROOT


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def render_kustomization(directory: Path) -> list[str]:
    kustomization = directory / "kustomization.yaml"
    if not kustomization.is_file():
        raise FileNotFoundError(f"missing kustomization: {kustomization.relative_to(ROOT)}")
    data = load_yaml(kustomization)
    resources = data.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError(f"resources must be a list in {kustomization.relative_to(ROOT)}")
    rendered: list[str] = []
    for resource in resources:
        resource_path = directory / resource
        if resource_path.is_dir():
            rendered.extend(render_kustomization(resource_path))
            continue
        if not resource_path.is_file():
            raise FileNotFoundError(f"kustomization resource not found: {resource_path.relative_to(ROOT)}")
        if resource_path.suffix not in {".yaml", ".yml"}:
            continue
        content = resource_path.read_text(encoding="utf-8").strip()
        if content:
            rendered.append(f"# Source: {resource_path.relative_to(ROOT)}\n{content}")
    return rendered


def main() -> int:
    try:
        chunks = render_kustomization(ROOT / "platform/kong/synthetic-apis")
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"Synthetic API render failed: {exc}")
        return 1
    print("\n---\n".join(chunks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
