#!/usr/bin/env python3
"""Render the Kong OSS baseline without applying it."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "platform/kong/versions.yaml"
VALUES = ROOT / "platform/kong/helm/values-kong-oss-baseline.yaml"


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


def render_helm() -> tuple[int, str]:
    helm = shutil.which("helm")
    if not helm:
        return 1, "Helm is required for Kong chart rendering. Install helm and rerun make render-kong-baseline."

    versions = load_yaml(VERSIONS)
    chart = versions["helm"]["chart_name"]
    chart_version = versions["helm"]["chart_version"]
    namespace = versions["deployment"]["namespace"]

    command = [
        helm,
        "template",
        "banklab-kong",
        chart,
        "--version",
        chart_version,
        "--namespace",
        namespace,
        "--values",
        str(VALUES),
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.returncode, result.stdout.strip()


def main() -> int:
    try:
        static_chunks = render_kustomization(ROOT / "platform/kong")
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"Kong static render failed: {exc}")
        return 1

    helm_code, helm_output = render_helm()
    if helm_code != 0:
        print(helm_output)
        return helm_code

    print("# Kong static resources")
    print("\n---\n".join(static_chunks))
    print("\n---\n# Kong Helm render")
    print(helm_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
