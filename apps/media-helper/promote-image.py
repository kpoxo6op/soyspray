"""Promote a tested digest without changing the media helper runtime configuration."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/media-helper@sha256:[0-9a-f]{64}"


def promote(image, app):
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested media-helper GHCR digest is required.")
    path, package_path = app / "manifests/deployment.yaml", app / "kustomization.yaml"
    deployment, package = yaml.safe_load(path.read_text()), yaml.safe_load(package_path.read_text())
    if (
        deployment.get("kind"),
        deployment.get("metadata", {}).get("name"),
        deployment.get("metadata", {}).get("namespace"),
    ) != ("Deployment", "media-helper", None):
        raise ValueError("Expected the existing media-helper Deployment in its namespaced package.")
    if package.get("namespace") != "media":
        raise ValueError("Keep the existing shared media namespace.")
    pod = deployment["spec"]["template"]["spec"]
    containers = [c for c in pod["containers"] if c["name"] == "media-helper"]
    if len(containers) != 1 or containers[0].get("args"):
        raise ValueError("Expected one helper container with no argument override.")
    container = containers[0]
    generators = package.get("configMapGenerator", [])
    code_mounts = [
        m
        for m in container.get("volumeMounts", [])
        if m["name"] == "code" or m["mountPath"].rstrip("/").startswith("/app")
    ]
    code_volumes = [v for v in pod.get("volumes", []) if v["name"] == "code"]
    code_generators = [g for g in generators if g["name"] == "media-helper-code"]
    if (
        not re.fullmatch(IMAGE, container["image"])
        or container.get("command")
        or container.get("readinessProbe") != {"httpGet": {"path": "/ready", "port": "http"}}
        or code_mounts
        or code_volumes
        or code_generators
    ):
        raise ValueError("Review unknown image or runtime overrides before promotion.")
    container["image"] = image
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
