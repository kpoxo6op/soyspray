#!/usr/bin/env python3
"""Validate the goal-003 synthetic bank API layer locally."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.synthetic_bank_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        BASE_LABELS,
        CLIENTS,
        EXTERNAL_RATE_LIMIT_PROFILE,
        FORBIDDEN_KINDS,
        INTERNAL_RATE_LIMIT_PROFILE,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_profile,
    )
except ModuleNotFoundError:
    from synthetic_bank_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        BASE_LABELS,
        CLIENTS,
        EXTERNAL_RATE_LIMIT_PROFILE,
        FORBIDDEN_KINDS,
        INTERNAL_RATE_LIMIT_PROFILE,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_profile,
    )


REQUIRED_ROOT_FILES = [
    "apis/synthetic-bank/README.md",
    "apis/synthetic-bank/versions.yaml",
    "apis/synthetic-bank/kustomization.yaml",
    "apis/synthetic-bank/api-catalog.yaml",
    "apis/synthetic-bank/route-matrix.yaml",
    "apis/synthetic-bank/exposure-policy.yaml",
    "clients/synthetic/client-catalog.yaml",
    "docs/api-catalog/index.md",
    "docs/architecture/synthetic-bank-apis.md",
    "docs/architecture/api-product-model.md",
    "docs/architecture/synthetic-client-model.md",
    "docs/architecture/goal-003-runtime-boundary.md",
    "docs/runbooks/synthetic-api-onboarding.md",
    "docs/runbooks/synthetic-api-runtime-smoke.md",
    "docs/runbooks/synthetic-api-rollback.md",
    "platform/kong/synthetic-apis/kustomization.yaml",
    "platform/kong/synthetic-apis/kong-allow-synthetic-api-upstreams.yaml",
    "platform/kong/synthetic-apis/argocd/synthetic-bank-apis-app.yaml",
    "scripts/render_synthetic_api_tenant_namespaces.py",
    "reports/synthetic-api-runtime-evidence.md",
    "reports/synthetic-api-route-smoke-results.md",
    "reports/synthetic-api-negative-test-results.md",
]

API_FILES = [
    "README.md",
    "openapi.yaml",
    "ownership.yaml",
    "kustomization.yaml",
    "configmap-mock-responses.yaml",
    "deployment.yaml",
    "service.yaml",
    "networkpolicy-allow-kong.yaml",
    "tests/positive.yaml",
    "tests/negative.yaml",
]

SECRET_NAME_MARKERS = (".env", "id_rsa", "id_ed25519", "kubeconfig", "admin.conf", "auth-profiles.json")
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


def load_yaml(path: str | Path) -> Any:
    full = ROOT / path if isinstance(path, str) else path
    return yaml.safe_load(full.read_text(encoding="utf-8"))


def yaml_docs(path: Path) -> list[dict[str, Any]]:
    return [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(doc, dict)]


def git_files() -> list[str]:
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True, check=True, stdout=subprocess.PIPE)
    return [line for line in result.stdout.splitlines() if line]


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def has_secret_like_name(path: str) -> bool:
    name = Path(path).name.lower()
    lower_path = path.lower()
    return name in SECRET_NAME_MARKERS or any(name.endswith(suffix) for suffix in SECRET_SUFFIXES) or lower_path.endswith("/.kube/config")


def check_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_ROOT_FILES:
        require((ROOT / relative).is_file(), errors, f"missing required file: {relative}")
    for api in APIS:
        route_file = "httproute-external.yaml" if api.exposure == "external" else "httproute-internal.yaml"
        for relative in API_FILES + [route_file]:
            path = ROOT / "apis/synthetic-bank" / api.key / relative
            require(path.is_file(), errors, f"missing {api.key} file: {path.relative_to(ROOT)}")
        wrong_route = "httproute-internal.yaml" if api.exposure == "external" else "httproute-external.yaml"
        require(not (ROOT / "apis/synthetic-bank" / api.key / wrong_route).exists(), errors, f"{api.key} has wrong exposure route file: {wrong_route}")
    for client in CLIENTS:
        require((ROOT / "clients/synthetic" / f"{client}.yaml").is_file(), errors, f"missing synthetic client: {client}")


def check_metadata(errors: list[str]) -> None:
    route_matrix = load_yaml("apis/synthetic-bank/route-matrix.yaml")["routes"]
    exposure = load_yaml("apis/synthetic-bank/exposure-policy.yaml")
    catalog = load_yaml("apis/synthetic-bank/api-catalog.yaml")["apis"]
    require(exposure["external_allowed"] == ["open-banking"], errors, "only open-banking may be externally allowed")
    require(exposure["authentication_required"] == AUTH_STATE, errors, "exposure policy must require key auth")
    require(exposure["authorization_required"] == AUTHORIZATION_PROFILE, errors, "exposure policy must require ACL authorization")
    require(exposure["rate_limiting_required"] == "goal004-redis-rate-limits", errors, "exposure policy must require Redis rate limiting")
    require(exposure["credential_source"] == RUNTIME_CREDENTIAL_SOURCE, errors, "exposure policy must keep credentials runtime-only")
    routes_by_api = {route["api"]: route for route in route_matrix}
    catalog_by_api = {entry["key"]: entry for entry in catalog}
    for api in APIS:
        ownership = load_yaml(ROOT / "apis/synthetic-bank" / api.key / "ownership.yaml")
        route = routes_by_api.get(api.key)
        catalog_entry = catalog_by_api.get(api.key)
        require(route is not None, errors, f"missing route matrix entry for {api.key}")
        require(catalog_entry is not None, errors, f"missing catalog entry for {api.key}")
        require(ownership["api_name"] == f"synthetic-{api.key}-api", errors, f"{api.key} api_name mismatch")
        require(ownership["tenant_namespace"] == api.namespace, errors, f"{api.key} namespace mismatch")
        require(ownership["owning_team"] == api.owner, errors, f"{api.key} owner mismatch")
        require(ownership["exposure"] == api.exposure, errors, f"{api.key} exposure mismatch")
        require(ownership["lifecycle_state"] == "sandbox", errors, f"{api.key} lifecycle mismatch")
        require(ownership["data_classification"] == "synthetic", errors, f"{api.key} classification mismatch")
        require(ownership["auth_profile"] == AUTH_PROFILE, errors, f"{api.key} auth profile mismatch")
        require(ownership["auth_state"] == AUTH_STATE, errors, f"{api.key} auth state mismatch")
        require(ownership["auth_plugin"] == api_auth_plugin(api.key), errors, f"{api.key} auth plugin mismatch")
        require(ownership["authorization_profile"] == AUTHORIZATION_PROFILE, errors, f"{api.key} authorization profile mismatch")
        require(ownership["access_group"] == api_access_group(api.key), errors, f"{api.key} access group mismatch")
        require(ownership["rate_limit_profile"] == api_rate_limit_profile(api.exposure), errors, f"{api.key} rate limit profile mismatch")
        require(ownership["credential_source"] == RUNTIME_CREDENTIAL_SOURCE, errors, f"{api.key} credential source mismatch")
        if route:
            require(route["host"] == api.host, errors, f"{api.key} host mismatch")
            require(route["path_prefix"] == api.prefix, errors, f"{api.key} path prefix mismatch")
            require(route["parent"] == f"platform-kong/{api.gateway}", errors, f"{api.key} parent mismatch")
            require(route["exposure"] == api.exposure, errors, f"{api.key} route exposure mismatch")
            require(route["auth_profile"] == AUTH_PROFILE, errors, f"{api.key} route auth profile mismatch")
            require(route["auth_state"] == AUTH_STATE, errors, f"{api.key} route auth state mismatch")
            require(route["auth_plugin"] == api_auth_plugin(api.key), errors, f"{api.key} route auth plugin mismatch")
            require(route["authorization_profile"] == AUTHORIZATION_PROFILE, errors, f"{api.key} route authorization profile mismatch")
            require(route["rate_limit_profile"] == api_rate_limit_profile(api.exposure), errors, f"{api.key} route rate limit profile mismatch")
        if catalog_entry:
            require(catalog_entry["auth_profile"] == AUTH_PROFILE, errors, f"{api.key} catalog auth profile mismatch")
            require(catalog_entry["auth_state"] == AUTH_STATE, errors, f"{api.key} catalog auth state mismatch")
            require(catalog_entry["auth_plugin"] == api_auth_plugin(api.key), errors, f"{api.key} catalog auth plugin mismatch")
            require(catalog_entry["authorization_profile"] == AUTHORIZATION_PROFILE, errors, f"{api.key} catalog authorization profile mismatch")
            require(catalog_entry["rate_limit_profile"] == api_rate_limit_profile(api.exposure), errors, f"{api.key} catalog rate limit profile mismatch")
    clients = load_yaml("clients/synthetic/client-catalog.yaml")["clients"]
    require({client["client_name"] for client in clients} == set(CLIENTS), errors, "client catalog does not match required clients")
    for client in clients:
        require(client["credentials_created"] == RUNTIME_CREDENTIAL_SOURCE, errors, f"{client['client_name']} credential source mismatch")
        require(client["current_auth_state"] == AUTH_STATE, errors, f"{client['client_name']} auth state mismatch")
        require(client["credential_secret_namespace"] == "synthetic-clients", errors, f"{client['client_name']} credential namespace mismatch")
        require(client["data_classification"] == "synthetic", errors, f"{client['client_name']} classification mismatch")


def check_manifests(errors: list[str]) -> None:
    image = load_yaml("apis/synthetic-bank/versions.yaml")["mock_backend"]["image"]
    synthetic_layer_kustomization = load_yaml("platform/kong/synthetic-apis/kustomization.yaml")
    require(
        "kong-allow-synthetic-api-upstreams.yaml" in synthetic_layer_kustomization.get("resources", []),
        errors,
        "synthetic API layer must include Kong egress allow policy",
    )
    kong_egress = load_yaml("platform/kong/synthetic-apis/kong-allow-synthetic-api-upstreams.yaml")
    require(kong_egress.get("kind") == "NetworkPolicy", errors, "Kong synthetic upstream allow policy must be a NetworkPolicy")
    require(kong_egress.get("metadata", {}).get("namespace") == "platform-kong", errors, "Kong synthetic upstream allow policy must live in platform-kong")
    require(
        kong_egress.get("spec", {}).get("podSelector", {}).get("matchLabels", {}).get("banklab.konghq.com/component") == "gateway",
        errors,
        "Kong synthetic upstream allow policy must select gateway pods",
    )
    egress_rules = kong_egress.get("spec", {}).get("egress", [])
    require(len(egress_rules) == 1, errors, "Kong synthetic upstream allow policy must have one bounded egress rule")
    if egress_rules:
        rule = egress_rules[0]
        require(rule.get("ports") == [{"protocol": "TCP", "port": 8080}], errors, "Kong synthetic upstream allow policy must restrict TCP 8080")
        allowed_namespaces = {
            peer.get("namespaceSelector", {}).get("matchLabels", {}).get("kubernetes.io/metadata.name")
            for peer in rule.get("to", [])
        }
        require(allowed_namespaces == {api.namespace for api in APIS}, errors, "Kong synthetic upstream allow policy namespace set mismatch")
        for peer in rule.get("to", []):
            labels = peer.get("podSelector", {}).get("matchLabels", {})
            require(labels.get("banklab.konghq.com/platform-layer") == "synthetic-api", errors, "Kong synthetic upstream allow policy must target synthetic API pods")
            require(labels.get("banklab.konghq.com/goal") == "goal-003", errors, "Kong synthetic upstream allow policy must target goal-003 pods")
    require(":" in image and not image.endswith(":latest"), errors, "mock backend image must be pinned and not latest")
    for api in APIS:
        namespace_path = ROOT / "platform/namespaces" / f"{api.namespace}.yaml"
        require(namespace_path.is_file(), errors, f"missing tenant namespace prereq: {namespace_path.relative_to(ROOT)}")
        if namespace_path.is_file():
            namespace = load_yaml(namespace_path)
            labels = namespace.get("metadata", {}).get("labels", {})
            require(namespace.get("kind") == "Namespace", errors, f"{namespace_path.relative_to(ROOT)} must be a Namespace")
            require(namespace.get("metadata", {}).get("name") == api.namespace, errors, f"{namespace_path.relative_to(ROOT)} namespace name mismatch")
            require(labels.get("banklab.konghq.com/managed-by") == "gitops", errors, f"{namespace_path.relative_to(ROOT)} managed-by label mismatch")
            require(labels.get("banklab.konghq.com/platform-layer") == "prereq", errors, f"{namespace_path.relative_to(ROOT)} platform-layer must remain prereq")
            require(labels.get("banklab.konghq.com/environment") == "lab", errors, f"{namespace_path.relative_to(ROOT)} environment label mismatch")
            require(labels.get("banklab.konghq.com/data-classification") == "synthetic", errors, f"{namespace_path.relative_to(ROOT)} data-classification label mismatch")
            require(labels.get("banklab.konghq.com/owner") == api.owner, errors, f"{namespace_path.relative_to(ROOT)} owner label mismatch")

        base = ROOT / "apis/synthetic-bank" / api.key
        docs = []
        for path in base.glob("*.yaml"):
            if path.name in {"openapi.yaml", "ownership.yaml", "kustomization.yaml"}:
                continue
            docs.extend((path, doc) for doc in yaml_docs(path))
        for path, doc in docs:
            kind = doc.get("kind")
            require(kind not in FORBIDDEN_KINDS, errors, f"forbidden kind {kind} in {path.relative_to(ROOT)}")
            labels = doc.get("metadata", {}).get("labels", {})
            for key, value in BASE_LABELS.items():
                if kind == "HTTPRoute" and key == "banklab.konghq.com/auth-profile":
                    value = AUTH_PROFILE
                if kind == "HTTPRoute" and key == "banklab.konghq.com/auth-state":
                    value = AUTH_STATE
                if kind == "HTTPRoute" and key == "banklab.konghq.com/goal":
                    value = "goal-004"
                require(labels.get(key) == value, errors, f"{path.relative_to(ROOT)} missing label {key}={value}")
            if kind == "HTTPRoute":
                require(doc.get("metadata", {}).get("annotations", {}).get("konghq.com/plugins") == api_plugin_annotation(api.key), errors, f"{api.key} HTTPRoute must attach goal004 plugins")
                require(labels.get("banklab.konghq.com/authorization-profile") == AUTHORIZATION_PROFILE, errors, f"{api.key} HTTPRoute authorization profile mismatch")
                require(labels.get("banklab.konghq.com/rate-limit-profile") == api_rate_limit_profile(api.exposure), errors, f"{api.key} HTTPRoute rate limit profile mismatch")
            require(doc.get("metadata", {}).get("namespace") == api.namespace, errors, f"{path.relative_to(ROOT)} namespace mismatch")
            if kind == "Deployment":
                pod_spec = doc["spec"]["template"]["spec"]
                container = doc["spec"]["template"]["spec"]["containers"][0]
                require(container["image"] == image, errors, f"{api.key} deployment image must match versions.yaml")
                require(not container["image"].endswith(":latest"), errors, f"{api.key} uses latest image")
                require(container.get("resources"), errors, f"{api.key} deployment missing resources")
                security_context = container.get("securityContext", {})
                require(security_context.get("readOnlyRootFilesystem") is True, errors, f"{api.key} deployment must use readOnlyRootFilesystem")
                tmp_mount = next((mount for mount in container.get("volumeMounts", []) if mount.get("mountPath") == "/tmp"), None)
                require(tmp_mount is not None, errors, f"{api.key} deployment must mount writable /tmp for nginx")
                if tmp_mount is not None:
                    require(tmp_mount.get("name") == "tmp", errors, f"{api.key} /tmp mount must use tmp volume")
                    require(tmp_mount.get("readOnly") is not True, errors, f"{api.key} /tmp mount must be writable")
                    volumes = {volume.get("name"): volume for volume in pod_spec.get("volumes", [])}
                    tmp_volume = volumes.get(tmp_mount.get("name"))
                    require(tmp_volume is not None and "emptyDir" in tmp_volume, errors, f"{api.key} /tmp mount must be backed by emptyDir")
            if kind == "HTTPRoute":
                spec = doc["spec"]
                require(spec["hostnames"] == [api.host], errors, f"{api.key} hostname mismatch")
                require("*" not in spec["hostnames"][0], errors, f"{api.key} wildcard hostname forbidden")
                require(spec["parentRefs"][0]["name"] == api.gateway, errors, f"{api.key} wrong Gateway")
                require(spec["rules"][0]["matches"][0]["path"]["value"] == api.prefix, errors, f"{api.key} route prefix mismatch")
                require(spec["rules"][0]["matches"][0]["path"]["value"] != "/", errors, f"{api.key} catch-all route forbidden")
                require("admin" not in str(doc).lower(), errors, f"{api.key} must not route Admin API")
            if kind == "NetworkPolicy":
                ingress = doc["spec"].get("ingress", [])
                require(ingress, errors, f"{api.key} NetworkPolicy must allow intended Kong ingress")
                require(ingress[0]["ports"][0]["port"] == 8080, errors, f"{api.key} NetworkPolicy must restrict port 8080")


def check_runtime_boundaries(errors: list[str]) -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for target in ("synthetic-api-tenant-namespaces-apply", "synthetic-api-apply", "synthetic-api-rollback"):
        block = re.search(rf"^{target}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
        require(block is not None, errors, f"missing Makefile target: {target}")
        if block:
            require("require-cluster-mutation-permission.sh" in block.group("body"), errors, f"{target} must call mutation guard")
    for forbidden in (
        "synthetic-api-install-dry-run",
        "synthetic-api-tenant-namespaces-dry-run",
        "synthetic-api-tenant-namespaces-apply",
        "synthetic-api-apply",
        "synthetic-api-smoke",
        "synthetic-api-negative-test",
        "synthetic-api-rollback",
        "synthetic-api-runtime-ready",
    ):
        require(not re.search(rf"run:\s+make\s+{forbidden}(?:\s|$)", ci), errors, f"CI must not run {forbidden}")


def check_no_sensitive_files(errors: list[str]) -> None:
    unsafe = [path for path in git_files() if (ROOT / path).is_file() and not path.startswith("kubespray/") and has_secret_like_name(path)]
    require(not unsafe, errors, "secret-like file names are present: " + ", ".join(sorted(unsafe)))


def validate() -> list[str]:
    errors: list[str] = []
    check_required_files(errors)
    check_metadata(errors)
    check_manifests(errors)
    check_runtime_boundaries(errors)
    check_no_sensitive_files(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Synthetic bank API validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Synthetic bank API validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
