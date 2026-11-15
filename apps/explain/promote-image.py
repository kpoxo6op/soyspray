"""Pin a tested catalog image digest in the Deployment, changing nothing else."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/explain@sha256:[0-9a-f]{64}"
# Until the first image is published the Deployment names no digest, and Argo does not own the app yet.
UNPROMOTED = "ghcr.io/kpoxo6op/explain:unpromoted"


def promote(image, app):
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested explain GHCR digest is required.")
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    if (deployment.get("kind"), deployment.get("metadata", {}).get("name")) != (
        "Deployment",
        "explain",
    ):
        raise ValueError("Expected the explain Deployment.")
    containers = deployment["spec"]["template"]["spec"]["containers"]
    current = containers[0]["image"] if len(containers) == 1 else ""
    if containers[0]["name"] != "web" or not (
        re.fullmatch(IMAGE, current) or current == UNPROMOTED
    ):
        raise ValueError("Review unknown containers or image overrides before promotion.")
    containers[0]["image"] = image
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    promote(parser.parse_args().image, Path(__file__).resolve().parent)
