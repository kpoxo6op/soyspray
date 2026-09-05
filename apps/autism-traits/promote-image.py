"""Prepare a digest and the configuration needed to serve the embedded site."""

import argparse
import re
from pathlib import Path

import yaml

RETIRED_CONFIGS = {
    "autism-traits-nginx",
    "autism-traits-site-core",
    *{f"autism-traits-site-images-{letter}" for letter in "abcde"},
}


def promote(image, package):
    if not re.fullmatch(r"ghcr\.io/kpoxo6op/autism-traits@sha256:[0-9a-f]{64}", image):
        raise ValueError("A tested autism-traits image digest is required.")
    deployment_path = package / "deployment.yaml"
    kustomization_path = package / "kustomization.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    kustomization = yaml.safe_load(kustomization_path.read_text())
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
    if not web["image"].startswith(
        ("nginxinc/nginx-unprivileged:", "ghcr.io/kpoxo6op/autism-traits@sha256:")
    ):
        raise ValueError("Unexpected prior image; review the deployment before promotion.")
    web["image"] = image
    web["volumeMounts"] = [
        mount for mount in web["volumeMounts"] if mount["name"] not in {"site", "nginx-config"}
    ]
    pod["volumes"] = [
        volume for volume in pod["volumes"] if volume["name"] not in {"site", "nginx-config"}
    ]
    generators = [
        item
        for item in kustomization.get("configMapGenerator", [])
        if item["name"] not in RETIRED_CONFIGS
    ]
    if generators:
        kustomization["configMapGenerator"] = generators
    else:
        kustomization.pop("configMapGenerator", None)
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))
    kustomization_path.write_text(yaml.safe_dump(kustomization, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parents[2] / "kubernetes/autism-traits")
