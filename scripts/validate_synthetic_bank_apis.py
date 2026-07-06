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
    from scripts.synthetic_bank_config import APIS, BASE_LABELS, CLIENTS, FORBIDDEN_KINDS, ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, BASE_LABELS, CLIENTS, FORBIDDEN_KINDS, ROOT


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
    "platform/kong/synthetic-apis/argocd/synthetic-bank-apis-app.yaml",
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
    require(exposure["temporary_no_auth"] == "temporary-no-auth", errors, "exposure policy must mark temporary-no-auth posture")
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
        require(ownership["auth_profile"] == "none-temporary-goal003-sandbox", errors, f"{api.key} auth profile mismatch")
        require(ownership["auth_state"] == "temporary-no-auth", errors, f"{api.key} auth state mismatch")
        require(ownership["authorization_profile"] == "none-temporary-goal003-sandbox", errors, f"{api.key} authorization profile mismatch")
        require(ownership["rate_limit_profile"] == "deferred-goal004", errors, f"{api.key} rate limit profile mismatch")
        if route:
            require(route["host"] == api.host, errors, f"{api.key} host mismatch")
            require(route["path_prefix"] == api.prefix, errors, f"{api.key} path prefix mismatch")
            require(route["parent"] == f"platform-kong/{api.gateway}", errors, f"{api.key} parent mismatch")
            require(route["exposure"] == api.exposure, errors, f"{api.key} route exposure mismatch")
            require(route["auth_state"] == "temporary-no-auth", errors, f"{api.key} route auth state mismatch")
        if catalog_entry:
            require(catalog_entry["auth_state"] == "temporary-no-auth", errors, f"{api.key} catalog auth state mismatch")
    clients = load_yaml("clients/synthetic/client-catalog.yaml")["clients"]
    require({client["client_name"] for client in clients} == set(CLIENTS), errors, "client catalog does not match required clients")
    for client in clients:
        require(client["credentials_created"] is False, errors, f"{client['client_name']} must not create credentials")
        require(client["current_auth_state"] == "temporary-no-auth", errors, f"{client['client_name']} auth state mismatch")
        require(client["data_classification"] == "synthetic", errors, f"{client['client_name']} classification mismatch")


def check_manifests(errors: list[str]) -> None:
    image = load_yaml("apis/synthetic-bank/versions.yaml")["mock_backend"]["image"]
    require(":" in image and not image.endswith(":latest"), errors, "mock backend image must be pinned and not latest")
    for api in APIS:
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
                require(labels.get(key) == value, errors, f"{path.relative_to(ROOT)} missing label {key}={value}")
            require(doc.get("metadata", {}).get("namespace") == api.namespace, errors, f"{path.relative_to(ROOT)} namespace mismatch")
            if kind == "Deployment":
                container = doc["spec"]["template"]["spec"]["containers"][0]
                require(container["image"] == image, errors, f"{api.key} deployment image must match versions.yaml")
                require(not container["image"].endswith(":latest"), errors, f"{api.key} uses latest image")
                require(container.get("resources"), errors, f"{api.key} deployment missing resources")
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
    for target in ("synthetic-api-apply", "synthetic-api-rollback"):
        block = re.search(rf"^{target}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
        require(block is not None, errors, f"missing Makefile target: {target}")
        if block:
            require("require-cluster-mutation-permission.sh" in block.group("body"), errors, f"{target} must call mutation guard")
    for forbidden in ("synthetic-api-install-dry-run", "synthetic-api-apply", "synthetic-api-smoke", "synthetic-api-negative-test", "synthetic-api-rollback", "synthetic-api-runtime-ready"):
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
