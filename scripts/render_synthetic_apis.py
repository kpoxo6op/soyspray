#!/usr/bin/env python3
"""Render goal-003 synthetic API manifests without applying them."""

from __future__ import annotations

import argparse
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


def filter_chunks(chunks: list[str], include_kind: set[str], exclude_kind: set[str]) -> list[str]:
    filtered = []
    for chunk in chunks:
        doc = yaml.safe_load(chunk)
        if not isinstance(doc, dict):
            continue
        kind = doc.get("kind")
        if include_kind and kind not in include_kind:
            continue
        if exclude_kind and kind in exclude_kind:
            continue
        filtered.append(chunk)
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-kind", action="append", default=[], help="only render resources with this kind")
    parser.add_argument("--exclude-kind", action="append", default=[], help="exclude resources with this kind")
    args = parser.parse_args()

    try:
        chunks = render_kustomization(ROOT / "apis/synthetic-bank")
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"Synthetic API render failed: {exc}")
        return 1
    chunks = filter_chunks(chunks, set(args.include_kind), set(args.exclude_kind))
    print("\n---\n".join(chunks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
