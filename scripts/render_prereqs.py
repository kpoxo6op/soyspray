#!/usr/bin/env python3
"""Render simple prerequisite kustomization files without applying them."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
KUSTOMIZATION_PATHS = [
    "platform/namespaces",
    "platform/networking/metallb",
    "platform/networking/network-policies",
    "platform/certificates/cert-manager",
]


def load_kustomization(directory: Path) -> list[str]:
    path = directory / "kustomization.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"missing kustomization: {path.relative_to(ROOT)}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resources = data.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError(f"resources must be a list in {path.relative_to(ROOT)}")
    return resources


def render_directory(relative_dir: str) -> str:
    directory = ROOT / relative_dir
    rendered: list[str] = []
    for resource in load_kustomization(directory):
        resource_path = directory / resource
        if not resource_path.is_file():
            raise FileNotFoundError(
                f"kustomization resource not found: {resource_path.relative_to(ROOT)}"
            )
        content = resource_path.read_text(encoding="utf-8").strip()
        if content:
            rendered.append(f"# Source: {resource_path.relative_to(ROOT)}\n{content}")
    return "\n---\n".join(rendered)


def main() -> int:
    try:
        chunks = [render_directory(path) for path in KUSTOMIZATION_PATHS]
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"Prerequisite render failed: {exc}")
        return 1

    print("\n---\n".join(chunk for chunk in chunks if chunk))
    return 0


if __name__ == "__main__":
    sys.exit(main())

