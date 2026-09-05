"""Promote a tested image with the configuration needed to replace the frozen script mount."""

import argparse
import re
from pathlib import Path

import yaml

IMAGE = r"ghcr\.io/kpoxo6op/domain-health@sha256:[0-9a-f]{64}"


def promote(image, app):
    if not re.fullmatch(IMAGE, image):
        raise ValueError("A tested domain-health GHCR digest is required.")
    deployment_path = app / "manifests/deployment.yaml"
    package_path = app / "kustomization.yaml"
    deployment = yaml.safe_load(deployment_path.read_text())
    package = yaml.safe_load(package_path.read_text())
    if (
        deployment.get("kind"),
        deployment.get("metadata", {}).get("name"),
        deployment.get("metadata", {}).get("namespace"),
    ) != ("Deployment", "domain-health", "domain-health"):
        raise ValueError("The package must contain the existing domain-health Deployment.")
    pod = deployment["spec"]["template"]["spec"]
    containers = [container for container in pod["containers"] if container["name"] == "exporter"]
    if len(containers) != 1:
        raise ValueError("Expected one exporter container.")
    exporter = containers[0]
    legacy = exporter["image"] == "python:3.12-slim"
    if not legacy and not re.fullmatch(IMAGE, exporter["image"]):
        raise ValueError("Unexpected previous image; review the deployment before promotion.")
    if legacy:
        generators = package.get("configMapGenerator", [])
        expected = {
            "name": "domain-health-exporter",
            "files": ["domain-health-exporter.py=manifests/legacy-exporter.py"],
            "options": {"disableNameSuffixHash": True},
        }
        if [item for item in generators if item["name"] == "domain-health-exporter"] != [expected]:
            raise ValueError("The frozen runtime generator changed; review the source transition.")
        if exporter.get("command") != ["python3", "/app/domain-health-exporter.py"]:
            raise ValueError("The runtime command changed; review the source transition.")
        if [
            item for item in exporter.get("volumeMounts", []) if item["name"] == "exporter-script"
        ] != [{"name": "exporter-script", "mountPath": "/app", "readOnly": True}]:
            raise ValueError("The runtime mount changed; review the source transition.")
        if [item for item in pod.get("volumes", []) if item["name"] == "exporter-script"] != [
            {
                "name": "exporter-script",
                "configMap": {"name": "domain-health-exporter", "defaultMode": 0o555},
            }
        ]:
            raise ValueError("The runtime volume changed; review the source transition.")
        exporter.pop("command")
        exporter["volumeMounts"] = [
            item for item in exporter["volumeMounts"] if item["name"] != "exporter-script"
        ]
        pod["volumes"] = [item for item in pod["volumes"] if item["name"] != "exporter-script"]
        package["configMapGenerator"] = [
            item for item in generators if item["name"] != "domain-health-exporter"
        ]
        for obj, key in [
            (exporter, "volumeMounts"),
            (pod, "volumes"),
            (package, "configMapGenerator"),
        ]:
            if not obj[key]:
                obj.pop(key)
        pod["automountServiceAccountToken"] = False
        exporter["securityContext"] = {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "capabilities": {"drop": ["ALL"]},
            "seccompProfile": {"type": "RuntimeDefault"},
        }
    elif (
        exporter.get("command")
        or any(item["name"] == "exporter-script" for item in pod.get("volumes", []))
        or any(item["name"] == "exporter-script" for item in exporter.get("volumeMounts", []))
        or any(
            item["name"] == "domain-health-exporter"
            for item in package.get("configMapGenerator", [])
        )
    ):
        raise ValueError("The image still has legacy runtime settings; review them together.")
    exporter["image"] = image
    # Both documents are validated before either file changes. The workflow commits them together.
    deployment_path.write_text(yaml.safe_dump(deployment, sort_keys=False))
    package_path.write_text(yaml.safe_dump(package, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
