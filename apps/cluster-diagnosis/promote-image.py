"""Promote a tested cluster diagnosis image without changing its settings."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/cluster-diagnosis@sha256:[0-9a-f]{64}"


def promote(image, app):
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested cluster-diagnosis GHCR digest is required.")
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    if (
        deployment.get("kind"),
        deployment.get("metadata", {}).get("name"),
        deployment.get("metadata", {}).get("namespace"),
    ) != ("Deployment", "cluster-diagnosis", "monitoring"):
        raise ValueError("The package must contain the existing cluster-diagnosis Deployment.")
    containers = [
        container
        for container in deployment["spec"]["template"]["spec"]["containers"]
        if container["name"] == "diagnosis"
    ]
    if len(containers) != 1:
        raise ValueError("Expected one diagnosis container.")
    diagnosis = containers[0]
    if not re.fullmatch(IMAGE, diagnosis["image"]):
        raise ValueError("Unexpected previous image; review the deployment before promotion.")
    if diagnosis.get("args"):
        raise ValueError("Runtime overrides need a separate configuration review.")
    if diagnosis["command"] != ["python3", "/app/diagnosis.py"]:
        raise ValueError("The entrypoint must stay the reviewed diagnosis loop.")
    diagnosis["image"] = image
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
