from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = "apps/sewing-guide/manifests"
APPLICATION = "apps/sewing-guide/argocd/application.yaml"
PROJECT = "apps/sewing-guide/argocd/project.yaml"
SERVICE_IP = "10.233.23.98"


def load_yaml(path):
    return yaml.safe_load((ROOT / path).read_text())


def render_package() -> list[dict]:
    result = subprocess.run(
        ["kubectl", "kustomize", PACKAGE], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def resource(resources, kind, name=None):
    return next(
        item
        for item in resources
        if item["kind"] == kind and (name is None or item["metadata"]["name"] == name)
    )


def test_workload_is_restricted_and_serves_both_routes() -> None:
    resources = render_package()
    deployment = resource(resources, "Deployment", "sewing-guide")
    service = resource(resources, "Service")
    namespace = resource(resources, "Namespace")
    pod_spec = deployment["spec"]["template"]["spec"]
    web = pod_spec["containers"][0]

    assert namespace["metadata"]["name"] == "sewing-guide"
    assert namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"
    assert pod_spec["automountServiceAccountToken"] is False
    assert pod_spec["securityContext"]["runAsNonRoot"] is True
    assert web["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
        "readOnlyRootFilesystem": True,
        "runAsGroup": 101,
        "runAsUser": 101,
    }
    assert re.fullmatch(r"ghcr\.io/kpoxo6op/sewing-guide@sha256:[0-9a-f]{64}", web["image"])
    assert web["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert {port["name"] for port in web["ports"]} == {"http", "https"}
    assert service["spec"]["clusterIP"] == SERVICE_IP
    assert service["spec"]["ports"] == [
        {"name": "http", "port": 80, "targetPort": "http"},
        {"name": "https", "port": 443, "targetPort": "https"},
    ]
    tls_volume = next(volume for volume in pod_spec["volumes"] if volume["name"] == "tls")
    assert tls_volume["secret"]["secretName"] == "sewing-guide-tls"


def test_private_ingress_has_no_public_dns_and_tunnel_is_boxed_in() -> None:
    resources = render_package()
    ingress = resource(resources, "Ingress")
    annotations = ingress["metadata"]["annotations"]
    assert (
        annotations["external-dns.alpha.kubernetes.io/ingress-hostname-source"] == "annotation-only"
    )
    assert "external-dns.alpha.kubernetes.io/hostname" not in annotations
    assert ingress["spec"]["rules"][0]["host"] == "sewing.soyspray.vip"
    assert ingress["spec"]["tls"][0]["secretName"] == "sewing-guide-tls"

    connector = resource(resources, "Deployment", "sewing-guide-cloudflared")
    env = connector["spec"]["template"]["spec"]["containers"][0]["env"][0]
    assert env["valueFrom"]["secretKeyRef"] == {
        "name": "sewing-guide-cloudflared-token",
        "key": "token",
    }
    assert connector["spec"]["replicas"] == 2

    deny = resource(resources, "NetworkPolicy", "sewing-guide-default-deny")
    assert deny["spec"]["podSelector"] == {} and deny["spec"]["policyTypes"] == [
        "Ingress",
        "Egress",
    ]
    web = resource(resources, "NetworkPolicy", "sewing-guide-web")
    assert web["spec"]["egress"] == []
    calico = [r for r in resources if r["apiVersion"] == "crd.projectcalico.org/v1"]
    host_boundary = next(r for r in calico if r["kind"] == "GlobalNetworkPolicy")
    assert "namespace" not in host_boundary["metadata"]
    assert host_boundary["spec"]["ingress"][0]["destination"]["notNets"] == [f"{SERVICE_IP}/32"]
    assert len([r for r in calico if r["kind"] == "HostEndpoint"]) == 3
    boundary = next(
        r
        for r in calico
        if r["kind"] == "NetworkPolicy"
        and r["metadata"]["name"] == "sewing-guide-cloudflared-boundary"
    )
    assert boundary["spec"]["egress"][-1] == {"action": "Deny"}


def test_argo_registration_is_guarded() -> None:
    application = load_yaml(APPLICATION)
    project = load_yaml(PROJECT)
    assert (
        application["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
        == "Prune=false,Delete=false"
    )
    assert application["spec"]["project"] == "sewing-guide"
    assert application["spec"]["source"]["path"] == PACKAGE
    assert application["spec"]["destination"]["namespace"] == "sewing-guide"
    assert project["spec"]["destinations"][0]["namespace"] == "sewing-guide"
    root = load_yaml("argocd/kustomization.yaml")
    assert "../apps/sewing-guide/argocd" in root["resources"]
