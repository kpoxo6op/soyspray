from __future__ import annotations

import subprocess

import pytest
import yaml
from conftest import ROOT

PACKAGES = (
    "platform/kong/gateway-api",
    "platform/kong/network-policies",
    "platform/kong/smoke",
    "apis/synthetic-bank",
    "kubernetes/banklab/security",
    "kubernetes/banklab/tenancy",
    "kubernetes/banklab/governance",
    "kubernetes/banklab/customer-web",
    "kubernetes/banklab/docs-site",
    "playbooks/argocd/applications/kong-bank-lab/operator-dashboard",
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


def test_mock_config_changes_roll_api_deployments() -> None:
    result = subprocess.run(
        ["kubectl", "kustomize", "apis/synthetic-bank"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(result.stdout) if item]
    configs = {
        item["metadata"]["name"]
        for item in resources
        if item["kind"] == "ConfigMap" and "-mock-responses-" in item["metadata"]["name"]
    }
    references = {
        volume["configMap"]["name"]
        for item in resources
        if item["kind"] == "Deployment"
        for volume in item["spec"]["template"]["spec"]["volumes"]
        if "configMap" in volume
    }

    assert len(configs) == 6
    assert references == configs
    assert "mock-config-revision" not in result.stdout


def test_customer_config_changes_roll_deployments() -> None:
    result = subprocess.run(
        ["kubectl", "kustomize", "kubernetes/banklab/customer-web"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(result.stdout) if item]
    configs = {item["metadata"]["name"] for item in resources if item["kind"] == "ConfigMap"}
    references = {
        volume["configMap"]["name"]
        for item in resources
        if item["kind"] == "Deployment"
        for volume in item["spec"]["template"]["spec"]["volumes"]
        if "configMap" in volume
    }

    assert len(configs) == 2
    assert references == configs


def test_docs_site_publishes_selected_git_revision_with_tls() -> None:
    result = subprocess.run(
        ["kubectl", "kustomize", "kubernetes/banklab/docs-site"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(result.stdout) if item]
    deployment = next(item for item in resources if item["kind"] == "Deployment")
    ingress = next(item for item in resources if item["kind"] == "Ingress")
    policy = next(item for item in resources if item["kind"] == "NetworkPolicy")
    containers = {
        container["name"]: container
        for container in deployment["spec"]["template"]["spec"]["containers"]
    }

    assert set(containers) == {"git-sync", "builder", "web"}
    assert any(
        arg.startswith("--repo=https://github.com/") for arg in containers["git-sync"]["args"]
    )
    assert "--ref=HEAD" in containers["git-sync"]["args"]
    assert containers["builder"]["image"].startswith("squidfunk/mkdocs-material:9.7.6@sha256:")
    assert {mount["mountPath"] for mount in containers["builder"]["volumeMounts"]} >= {
        "/repo",
        "/site",
        "/tmp",
    }
    assert containers["web"]["securityContext"]["runAsUser"] == 101
    pod_spec = deployment["spec"]["template"]["spec"]
    assert pod_spec["automountServiceAccountToken"] is False
    assert ingress["spec"]["tls"] == [
        {"hosts": ["banklab-docs.soyspray.vip"], "secretName": "banklab-docs-tls"}
    ]
    assert any(
        port == {"protocol": "TCP", "port": 443}
        for rule in policy["spec"]["egress"]
        for port in rule["ports"]
    )

    app_text = (
        ROOT / "playbooks/argocd/applications/kong-bank-lab/banklab-docs-application.yaml"
    ).read_text()
    rendered = app_text.replace("targetRevision: HEAD", "targetRevision: test-branch").replace(
        "--ref=HEAD", "--ref=test-branch"
    )
    app = yaml.safe_load(rendered)
    assert app["spec"]["source"]["targetRevision"] == "test-branch"
    assert "--ref=test-branch" in app["spec"]["source"]["kustomize"]["patches"][0]["patch"]


@pytest.mark.parametrize(
    "path",
    (
        "platform/kong/smoke",
        "apis/synthetic-bank",
        "kubernetes/banklab/security",
        "kubernetes/banklab/customer-web",
        "kubernetes/banklab/docs-site",
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
        "platform/kong/smoke",
        "kubernetes/banklab/security",
        "kubernetes/banklab/tenancy",
        "kubernetes/banklab/docs-site",
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
        "platform-kong-smoke",
        "synthetic-clients",
        "banklab-docs",
        "tenant-accounts",
        "tenant-payments",
        "tenant-cards",
        "tenant-customer-profile",
        "tenant-fraud",
        "tenant-open-banking",
    }
    assert expected <= namespaces.keys()
    for name in expected:
        labels = namespaces[name]["metadata"]["labels"]
        assert labels["pod-security.kubernetes.io/enforce"] == "restricted"
        assert labels["pod-security.kubernetes.io/enforce-version"] == "v1.35"
