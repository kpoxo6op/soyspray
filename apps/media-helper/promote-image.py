"""Promote a tested digest with the configuration that removes the frozen code mount."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/media-helper@sha256:[0-9a-f]{64}"
LEGACY = (
    "python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d"
)


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
    if container["image"] == LEGACY:
        if container.get("command") != ["python", "/app/app.py"]:
            raise ValueError("Review the changed runtime command before promotion.")
        if container.get("readinessProbe") != {"httpGet": {"path": "/healthz", "port": "http"}}:
            raise ValueError("Review the changed readiness probe before promotion.")
        if code_mounts != [{"name": "code", "mountPath": "/app", "readOnly": True}]:
            raise ValueError("Review the changed runtime mount before promotion.")
        if code_volumes != [
            {
                "name": "code",
                "configMap": {
                    "name": "media-helper-code",
                    "items": [
                        {"key": "app.py", "path": "app.py"},
                        {"key": "channels.json", "path": "channels.json"},
                    ],
                },
            }
        ]:
            raise ValueError("Review the changed code volume before promotion.")
        if code_generators != [
            {
                "name": "media-helper-code",
                "files": [
                    "app.py=manifests/legacy-app.py",
                    "channels.json=manifests/legacy-channels.json",
                ],
            }
        ]:
            raise ValueError("Review the changed frozen source before promotion.")
        container.pop("command")
        container["readinessProbe"]["httpGet"]["path"] = "/ready"
        container["volumeMounts"] = [m for m in container["volumeMounts"] if m["name"] != "code"]
        pod["volumes"] = [v for v in pod["volumes"] if v["name"] != "code"]
        package["configMapGenerator"] = [g for g in generators if g["name"] != "media-helper-code"]
        if not package["configMapGenerator"]:
            package.pop("configMapGenerator")
            package.pop("generatorOptions", None)
    elif (
        not re.fullmatch(IMAGE, container["image"])
        or container.get("command")
        or container.get("readinessProbe") != {"httpGet": {"path": "/ready", "port": "http"}}
        or code_mounts
        or code_volumes
        or code_generators
    ):
        raise ValueError("Review unknown image or runtime overrides before promotion.")
    container["image"] = image
    # Validate both documents before writing; the workflow commits their transition together.
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))
    package_path.write_text(yaml.safe_dump(package, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
