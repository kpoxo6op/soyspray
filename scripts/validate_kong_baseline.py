#!/usr/bin/env python3
"""Validate goal-002 Kong OSS baseline files without requiring a cluster."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "platform/kong/README.md",
    "platform/kong/versions.yaml",
    "platform/kong/namespace.yaml",
    "platform/kong/kustomization.yaml",
    "platform/kong/helm/README.md",
    "platform/kong/helm/values-kong-oss-baseline.yaml",
    "platform/kong/helm/values-kong-oss-baseline.schema.yaml",
    "platform/kong/helm/render-kong-baseline.sh",
    "platform/kong/gateway-api/README.md",
    "platform/kong/gateway-api/crds/standard-install.yaml",
    "platform/kong/gateway-api/kustomization.yaml",
    "platform/kong/gateway-api/gateway-api-crds.README.md",
    "platform/kong/gateway-api/gatewayclass-kong.yaml",
    "platform/kong/gateway-api/gateway-external.yaml",
    "platform/kong/gateway-api/gateway-internal.yaml",
    "platform/kong/network-policies/README.md",
    "platform/kong/network-policies/kustomization.yaml",
    "platform/kong/network-policies/kong-default-deny.yaml",
    "platform/kong/network-policies/kong-allow-dns.yaml",
    "platform/kong/network-policies/kong-allow-kube-api-placeholder.yaml",
    "platform/kong/network-policies/kong-allow-proxy-ingress.yaml",
    "platform/kong/network-policies/kong-allow-controller-admin.yaml",
    "platform/kong/network-policies/kong-allow-admin-from-controller.yaml",
    "platform/kong/network-policies/kong-allow-smoke-upstream.yaml",
    "platform/kong/smoke/README.md",
    "platform/kong/smoke/kustomization.yaml",
    "platform/kong/smoke/namespace.yaml",
    "platform/kong/smoke/deployment.yaml",
    "platform/kong/smoke/service.yaml",
    "platform/kong/smoke/httproute-external.yaml",
    "platform/kong/smoke/httproute-internal.yaml",
    "platform/kong/argocd/README.md",
    "platform/kong/argocd/kong-baseline-app.yaml",
    "platform/kong/argocd/kong-gateway-api-app.yaml",
    "platform/kong/argocd/kong-smoke-app.yaml",
    "platform/kong/scripts/README.md",
    "platform/kong/scripts/check-kong-baseline.sh",
    "platform/kong/scripts/check-admin-not-exposed.sh",
    "platform/kong/scripts/route-smoke.sh",
    "platform/kong/scripts/render-and-lint-kong.sh",
    "platform/gitops/app-of-apps/kong-baseline-app.yaml",
    "docs/architecture/kong-oss-baseline.md",
    "docs/architecture/gateway-api-baseline.md",
    "docs/architecture/kong-admin-api-exposure.md",
    "docs/architecture/kong-baseline-testing.md",
    "docs/runbooks/kong-baseline-install.md",
    "docs/runbooks/kong-baseline-rollback.md",
    "docs/runbooks/kong-admin-api-exposure-check.md",
    "tests/unit/test_goal_002_kong_structure.py",
    "tests/unit/test_goal_002_kong_versions.py",
    "tests/unit/test_goal_002_no_enterprise_features.py",
    "tests/unit/test_goal_002_admin_api_private.py",
    "tests/policy/test_goal_002_kong_policy.py",
    "tests/policy/test_goal_002_no_forbidden_kong_resources.py",
    "scripts/validate_kong_baseline.py",
    "scripts/render_kong_baseline.py",
    "scripts/check_kong_cluster.py",
    "reports/goal-002-summary.md",
]

FORBIDDEN_KINDS = {
    "KongPlugin",
    "KongClusterPlugin",
    "KongConsumer",
    "KongConsumerGroup",
    "KongIngress",
    "TCPIngress",
    "UDPIngress",
    "Secret",
}

FORBIDDEN_TEXT = (
    "kong/kong-gateway",
    "openid-connect",
    "request-validator",
    "mtls-auth",
    "key-auth",
    "jwt",
    "rate-limiting",
)

SECRET_KEY_RE = re.compile(r"(password|secret|token|private[_-]?key|access[_-]?key)", re.I)
PLACEHOLDERS = ("", "CHANGE_ME", "REPLACE_WITH", "PLACEHOLDER", "EXAMPLE", "{{", "$")


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def read_yaml(path: str) -> Any:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def yaml_docs(path: Path) -> list[dict[str, Any]]:
    return [
        doc
        for doc in yaml.safe_load_all(path.read_text(encoding="utf-8"))
        if isinstance(doc, dict)
    ]


def kong_yaml_files() -> list[Path]:
    files = [
        path
        for path in (ROOT / "platform/kong").rglob("*")
        if path.suffix in {".yaml", ".yml"}
        and "gateway-api/crds" not in path.as_posix()
    ]
    files.append(ROOT / "platform/gitops/app-of-apps/kong-baseline-app.yaml")
    return sorted(set(files))


def walk_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_values(item)


def is_placeholder(value: str) -> bool:
    upper = value.strip().strip('"').strip("'").upper()
    return any(marker in upper for marker in PLACEHOLDERS)


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def check_required_paths(errors: list[str]) -> None:
    for path in REQUIRED_FILES:
        require((ROOT / path).is_file(), errors, f"missing required file: {path}")


def check_versions(errors: list[str]) -> None:
    versions = read_yaml("platform/kong/versions.yaml")
    require(versions["kong_gateway"]["image_repository"] == "kong", errors, "Kong Gateway image repository must be kong")
    require(versions["kong_gateway"]["image_tag"] == "3.9.3", errors, "Kong Gateway image tag must be 3.9.3")
    require(versions["kong_gateway"]["mode"] == "dbless", errors, "Kong Gateway mode must be dbless")
    require(versions["kong_gateway"]["enterprise_enabled"] is False, errors, "Kong Enterprise must be disabled")
    require(
        versions["kong_ingress_controller"]["image_repository"] == "kong/kubernetes-ingress-controller",
        errors,
        "KIC image repository mismatch",
    )
    require(versions["kong_ingress_controller"]["image_tag"] == "3.5.10", errors, "KIC image tag must be 3.5.10")
    require(versions["helm"]["chart_name"] == "kong/ingress", errors, "Helm chart must be kong/ingress")
    require(versions["helm"]["chart_version"] == "0.24.0", errors, "Helm chart version must be pinned to 0.24.0")
    require(versions["gateway_api"]["version"] == "v1.3.0", errors, "Gateway API version must be v1.3.0")
    check_kic_gateway_api_compatibility(versions, errors)
    for key, value in walk_values(versions):
        if isinstance(value, str):
            require("REPLACE_WITH" not in value, errors, f"unresolved version placeholder for {key}")
            require(value.lower() != "latest", errors, f"latest version tag is forbidden for {key}")


def check_values(errors: list[str]) -> None:
    values = read_yaml("platform/kong/helm/values-kong-oss-baseline.yaml")
    gateway = values["gateway"]
    controller = values["controller"]
    require(gateway["image"]["repository"] == "kong", errors, "values must use kong OSS image")
    require(gateway["image"]["tag"] == "3.9.3", errors, "values must pin Kong tag 3.9.3")
    require(gateway["enterprise"]["enabled"] is False, errors, "enterprise.enabled must be false")
    require(gateway["env"]["database"] == "off", errors, "Kong must be DB-less")
    require(gateway["postgresql"]["enabled"] is False, errors, "Kong PostgreSQL must be disabled")
    require(gateway["admin"]["type"] == "ClusterIP", errors, "Admin API service must be ClusterIP")
    require(gateway["admin"]["ingress"]["enabled"] is False, errors, "Admin API ingress must be disabled")
    require(gateway["manager"]["enabled"] is False, errors, "Kong Manager must be disabled")
    require(gateway["portal"]["enabled"] is False, errors, "Kong Portal must be disabled")
    require(gateway["portalapi"]["enabled"] is False, errors, "Kong Portal API must be disabled")
    require(gateway["proxy"]["type"] == "LoadBalancer", errors, "Proxy service must be LoadBalancer")
    require(gateway["replicaCount"] == 2, errors, "Kong Gateway must start with two replicas")
    require(controller["ingressController"]["image"]["tag"] == "3.5.10", errors, "KIC tag must be pinned to 3.5.10")
    require(controller["ingressController"]["gatewayDiscovery"]["enabled"] is True, errors, "KIC gateway discovery must be enabled")


def parse_minor(version: str) -> tuple[int, int]:
    cleaned = version.strip().lstrip("v")
    major, minor, *_ = cleaned.split(".")
    return int(major), int(minor)


def check_kic_gateway_api_compatibility(versions: dict[str, Any], errors: list[str]) -> None:
    kic_tag = versions["kong_ingress_controller"]["image_tag"]
    gateway_api_version = versions["gateway_api"]["version"]
    if kic_tag.startswith("3.5."):
        major, minor = parse_minor(gateway_api_version)
        require(
            major == 1 and minor <= 3,
            errors,
            "KIC 3.5.x supports Gateway API up to v1.3.x according to Kong compatibility docs",
        )


def check_gateway_api(errors: list[str]) -> None:
    gateway_class = read_yaml("platform/kong/gateway-api/gatewayclass-kong.yaml")
    require(gateway_class["kind"] == "GatewayClass", errors, "gatewayclass-kong must be GatewayClass")
    require(
        gateway_class["spec"]["controllerName"] == "konghq.com/kic-gateway-controller",
        errors,
        "GatewayClass controllerName mismatch",
    )
    require(
        gateway_class["metadata"]["annotations"]["konghq.com/gatewayclass-unmanaged"] == "true",
        errors,
        "GatewayClass must be marked unmanaged",
    )
    external = read_yaml("platform/kong/gateway-api/gateway-external.yaml")
    internal = read_yaml("platform/kong/gateway-api/gateway-internal.yaml")
    require(external["spec"]["listeners"][0]["hostname"] == "*.external.banklab.test", errors, "external Gateway hostname mismatch")
    require(internal["spec"]["listeners"][0]["hostname"] == "*.internal.banklab.test", errors, "internal Gateway hostname mismatch")


def check_smoke(errors: list[str]) -> None:
    deployment = read_yaml("platform/kong/smoke/deployment.yaml")
    image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
    require(":" in image and not image.endswith(":latest"), errors, "smoke backend image must be pinned and not latest")
    for route_file, hostname, parent in [
        ("platform/kong/smoke/httproute-external.yaml", "kong-smoke.external.banklab.test", "kong-external"),
        ("platform/kong/smoke/httproute-internal.yaml", "kong-smoke.internal.banklab.test", "kong-internal"),
    ]:
        route = read_yaml(route_file)
        require(route["kind"] == "HTTPRoute", errors, f"{route_file} must be HTTPRoute")
        require(route["spec"]["hostnames"] == [hostname], errors, f"{route_file} hostname mismatch")
        require(route["spec"]["parentRefs"][0]["name"] == parent, errors, f"{route_file} parentRef mismatch")


def check_manifests(errors: list[str]) -> None:
    for path in kong_yaml_files():
        docs = yaml_docs(path)
        content = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(ROOT))
        for forbidden in FORBIDDEN_TEXT:
            require(forbidden not in content, errors, f"forbidden Kong feature text {forbidden} in {relative}")
        for doc in docs:
            kind = doc.get("kind")
            require(kind not in FORBIDDEN_KINDS, errors, f"forbidden kind {kind} in {relative}")
            if kind in {"Ingress", "Gateway", "HTTPRoute"}:
                require("admin" not in content.lower(), errors, f"Admin API must not be routed in {relative}")
            if kind == "Service" and "admin" in doc.get("metadata", {}).get("name", "").lower():
                service_type = doc.get("spec", {}).get("type", "ClusterIP")
                require(service_type not in {"LoadBalancer", "NodePort"}, errors, f"Admin service external exposure in {relative}")
        for key, value in walk_values(docs):
            if isinstance(value, str) and value.lower() == "latest":
                errors.append(f"latest image/tag value found in {relative}")
            if isinstance(value, str) and SECRET_KEY_RE.search(str(key)) and not is_placeholder(value):
                errors.append(f"non-placeholder secret-like value in {relative}: {key}")


def check_argocd(errors: list[str]) -> None:
    app_files = list((ROOT / "platform/kong/argocd").glob("*.yaml")) + [
        ROOT / "platform/gitops/app-of-apps/kong-baseline-app.yaml"
    ]
    for path in app_files:
        content = path.read_text(encoding="utf-8")
        require("REPLACE_WITH_REPO_URL" in content, errors, f"{path.relative_to(ROOT)} must keep repo URL placeholder")
        doc = yaml.safe_load(content)
        require(doc["kind"] == "Application", errors, f"{path.relative_to(ROOT)} must be an Argo CD Application")


def check_repo_files(errors: list[str]) -> None:
    for path in git_files():
        if not path.startswith("platform/kong/"):
            continue
        name = Path(path).name.lower()
        require(not name.endswith((".key", ".pem", ".p12", ".pfx")), errors, f"sensitive file suffix under platform/kong: {path}")
        require("kubeconfig" not in name, errors, f"kubeconfig file under platform/kong: {path}")


def validate(admin_only: bool = False) -> list[str]:
    errors: list[str] = []
    check_required_paths(errors)
    check_versions(errors)
    check_values(errors)
    check_gateway_api(errors)
    check_smoke(errors)
    check_manifests(errors)
    check_argocd(errors)
    check_repo_files(errors)
    if admin_only:
        return [error for error in errors if "Admin" in error or "admin" in error]
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-only", action="store_true")
    args = parser.parse_args()

    errors = validate(admin_only=args.admin_only)
    if errors:
        print("Kong baseline validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Kong baseline validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
