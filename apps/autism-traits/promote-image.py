"""Update the static site's image digest for promotion."""

import argparse
import re
from pathlib import Path

import yaml


def promote(image, package):
    if not re.fullmatch(r"ghcr\.io/kpoxo6op/autism-traits@sha256:[0-9a-f]{64}", image):
        raise ValueError("A tested autism-traits image digest is required.")
    deployment_path = package / "deployment.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    if (deployment.get("kind"), deployment.get("metadata", {}).get("name")) != (
        "Deployment",
        "autism-traits",
    ):
        raise ValueError("The package does not contain the expected Deployment.")
    pod = deployment["spec"]["template"]["spec"]
    containers = [container for container in pod["containers"] if container["name"] == "web"]
    if len(containers) != 1:
        raise ValueError("Expected one web container.")
    web = containers[0]
    if not re.fullmatch(r"ghcr\.io/kpoxo6op/autism-traits@sha256:[0-9a-f]{64}", web["image"]):
        raise ValueError("Unexpected prior image; review the deployment before promotion.")
    web["image"] = image
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent / "manifests")
