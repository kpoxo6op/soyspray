"""Promote a tested domain health image without changing its deployment settings."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/domain-health@sha256:[0-9a-f]{64}"


def promote(image, app):
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested domain-health GHCR digest is required.")
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    if (
        deployment.get("kind"),
        deployment.get("metadata", {}).get("name"),
        deployment.get("metadata", {}).get("namespace"),
    ) != ("Deployment", "domain-health", "domain-health"):
        raise ValueError("The package must contain the existing domain-health Deployment.")
    containers = [
        container
        for container in deployment["spec"]["template"]["spec"]["containers"]
        if container["name"] == "exporter"
    ]
    if len(containers) != 1:
        raise ValueError("Expected one exporter container.")
    exporter = containers[0]
    if not re.fullmatch(IMAGE, exporter["image"]):
        raise ValueError("Unexpected previous image; review the deployment before promotion.")
    if exporter.get("command") or exporter.get("args") or exporter.get("volumeMounts"):
        raise ValueError("Runtime overrides need a separate configuration review.")
    exporter["image"] = image
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
