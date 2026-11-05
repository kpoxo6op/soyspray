"""Promote a tested horoscope image without changing its deployment settings."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/otv-horoscope@sha256:[0-9a-f]{64}"


def promote(image: str, app: Path) -> None:
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested otv-horoscope GHCR digest is required.")
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    identity = (
        deployment.get("kind"),
        deployment.get("metadata", {}).get("name"),
        deployment.get("metadata", {}).get("namespace"),
    )
    if identity != ("Deployment", "otv-horoscope", "otv-horoscope"):
        raise ValueError("The package must contain the otv-horoscope Deployment.")
    containers = deployment["spec"]["template"]["spec"]["containers"]
    recorders = [container for container in containers if container["name"] == "recorder"]
    if len(containers) != 1 or len(recorders) != 1:
        raise ValueError("Expected exactly one recorder container.")
    recorder = recorders[0]
    if not re.fullmatch(IMAGE, recorder["image"]):
        raise ValueError("Unexpected previous image; review the deployment before promotion.")
    if recorder.get("command") or recorder.get("args"):
        raise ValueError("Runtime command overrides need a separate configuration review.")
    recorder["image"] = image
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
