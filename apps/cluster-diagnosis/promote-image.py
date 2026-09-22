"""Promote a tested cluster diagnosis image without changing its settings.

The manifest is edited as text. A parse-and-redump would reformat the file and
delete the comments that record why the pod has no liveness probe, why the
strategy is Recreate and why the pod carries no Kubernetes identity. The
promotion must be reviewable as a single changed digest.
"""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/cluster-diagnosis@sha256:[0-9a-f]{64}"


def promote(image, app):
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested cluster-diagnosis GHCR digest is required.")
    path = app / "manifests/deployment.yaml"
    text = path.read_text()
    deployment = yaml.safe_load(text)
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
    previous = diagnosis["image"]
    if not re.fullmatch(IMAGE, previous):
        raise ValueError("Unexpected previous image; review the deployment before promotion.")
    if diagnosis.get("args"):
        raise ValueError("Runtime overrides need a separate configuration review.")
    if diagnosis["command"] != ["python3", "/app/diagnosis.py"]:
        raise ValueError("The entrypoint must stay the reviewed diagnosis loop.")
    if previous == image:
        return False
    if text.count(previous) != 1:
        raise ValueError("The previous digest must appear exactly once in the manifest.")
    path.write_text(text.replace(previous, image))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
