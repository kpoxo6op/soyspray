from __future__ import annotations

import subprocess

import pytest
import yaml
from conftest import ROOT

PACKAGES = (
    "kubernetes/autism-traits",
    "kubernetes/boys",
)


@pytest.mark.parametrize("path", PACKAGES)
def test_kustomize_package_renders(path: str) -> None:
    result = subprocess.run(
        ["kubectl", "kustomize", path],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "apiVersion:" in result.stdout


@pytest.mark.parametrize(
    "path",
    (
        "kubernetes/autism-traits",
        "kubernetes/boys",
    ),
)
def test_application_workloads_use_the_restricted_baseline(path: str) -> None:
    result = subprocess.run(
        ["kubectl", "kustomize", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(result.stdout) if item]
    deployments = [item for item in resources if item["kind"] == "Deployment"]
    assert deployments

    for deployment in deployments:
        pod = deployment["spec"]["template"]["spec"]
        assert pod["automountServiceAccountToken"] is False
        assert pod["securityContext"]["runAsNonRoot"] is True
        assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
        for container in pod["containers"]:
            assert container["resources"]["requests"]
            assert container["resources"]["limits"]
            assert container["securityContext"]["allowPrivilegeEscalation"] is False
            assert container["securityContext"]["readOnlyRootFilesystem"] is True
            assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
            assert "@sha256:" in container["image"]


def test_application_namespaces_enforce_restricted_pod_security() -> None:
    paths = (
        "kubernetes/autism-traits",
        "kubernetes/boys",
    )
    namespaces = {}
    for path in paths:
        result = subprocess.run(
            ["kubectl", "kustomize", path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for resource in yaml.safe_load_all(result.stdout):
            if resource and resource["kind"] == "Namespace":
                namespaces[resource["metadata"]["name"]] = resource

    expected = {
        "boys",
    }
    assert expected <= namespaces.keys()
    for name in expected:
        labels = namespaces[name]["metadata"]["labels"]
        assert labels["pod-security.kubernetes.io/enforce"] == "restricted"
        assert labels["pod-security.kubernetes.io/enforce-version"] == "v1.35"
