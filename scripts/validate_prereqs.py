#!/usr/bin/env python3
"""Validate goal-001 platform prerequisites locally."""

from __future__ import annotations

import base64
import binascii
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_NAMESPACES = {
    "platform-system": "platform-team",
    "platform-gitops": "platform-team",
    "platform-security": "security-team",
    "platform-networking": "platform-networking-team",
    "platform-observability": "platform-observability-team",
    "platform-identity": "platform-identity-team",
    "tenant-accounts": "tenant-accounts-team",
    "tenant-payments": "tenant-payments-team",
    "tenant-cards": "tenant-cards-team",
    "tenant-customer-profile": "tenant-customer-profile-team",
    "tenant-fraud": "tenant-fraud-team",
    "tenant-open-banking": "tenant-open-banking-team",
    "synthetic-clients": "synthetic-client-team",
}

REQUIRED_LABELS = {
    "banklab.konghq.com/managed-by": "gitops",
    "banklab.konghq.com/platform-layer": "prereq",
    "banklab.konghq.com/environment": "lab",
    "banklab.konghq.com/data-classification": "synthetic",
}

REQUIRED_DIRS = [
    "platform/namespaces",
    "platform/gitops/app-of-apps",
    "platform/gitops/projects",
    "platform/networking/metallb",
    "platform/networking/network-policies",
    "platform/security/sops",
    "platform/security/policies",
    "platform/certificates/cert-manager",
    "platform/bootstrap",
]

REQUIRED_FILES = [
    "platform/namespaces/kustomization.yaml",
    "platform/gitops/app-of-apps/root-app.yaml",
    "platform/gitops/app-of-apps/platform-prereqs-app.yaml",
    "platform/gitops/app-of-apps/namespaces-app.yaml",
    "platform/gitops/app-of-apps/networking-app.yaml",
    "platform/gitops/app-of-apps/security-app.yaml",
    "platform/gitops/app-of-apps/cert-manager-app.yaml",
    "platform/gitops/app-of-apps/metallb-app.yaml",
    "platform/gitops/projects/platform-project.yaml",
    "platform/gitops/projects/security-project.yaml",
    "platform/gitops/projects/tenant-project-template.yaml",
    "platform/networking/metallb/kustomization.yaml",
    "platform/networking/metallb/namespace.yaml",
    "platform/networking/metallb/helm-values.yaml",
    "platform/networking/metallb/ip-address-pool.example.yaml",
    "platform/networking/metallb/l2-advertisement.example.yaml",
    "platform/networking/network-policies/kustomization.yaml",
    "platform/networking/network-policies/platform-default-deny.yaml",
    "platform/networking/network-policies/tenants-default-deny.yaml",
    "platform/networking/network-policies/allow-dns.yaml",
    "platform/networking/network-policies/allow-gitops-to-managed-namespaces.yaml",
    "platform/networking/network-policies/allow-observability-scrape-placeholder.yaml",
    "platform/networking/network-policies/allow-ingress-controller-placeholder.yaml",
    "platform/security/sops/.sops.yaml.example",
    "platform/security/sops/encrypted-secret.example.yaml",
    "platform/security/policies/namespace-labels.md",
    "platform/certificates/cert-manager/kustomization.yaml",
    "platform/certificates/cert-manager/namespace.yaml",
    "platform/certificates/cert-manager/helm-values.yaml",
    "platform/certificates/cert-manager/cluster-issuer-selfsigned.example.yaml",
    "platform/certificates/cert-manager/cluster-issuer-banklab-ca.example.yaml",
    "platform/bootstrap/apply-prereqs.example.sh",
    "platform/bootstrap/check-cluster-prereqs.sh",
    "docs/architecture/platform-prerequisites.md",
    "docs/architecture/gitops-bootstrap.md",
    "docs/architecture/network-policy-baseline.md",
    "docs/architecture/secrets-management.md",
    "docs/architecture/certificate-management.md",
    "docs/architecture/home-lab-networking.md",
    "docs/runbooks/platform-prereqs-rollback.md",
    "docs/runbooks/network-policy-recovery.md",
    "reports/goal-001-summary.md",
]

FORBIDDEN_KONG_KINDS = {
    "GatewayClass",
    "Gateway",
    "HTTPRoute",
    "KongPlugin",
    "KongClusterPlugin",
    "KongConsumer",
    "KongIngress",
    "TCPIngress",
    "UDPIngress",
}

SECRET_KEY_RE = re.compile(r"(password|secret|token|private[_-]?key|access[_-]?key)", re.I)
PLACEHOLDER_MARKERS = ("CHANGE_ME", "REPLACE_WITH", "EXAMPLE", "PLACEHOLDER", "{{", "$")
KNOWN_BAD_MARKERS = (
    "book" + "lore123",
    "password: " + "immich",
    "Ym9v" + "a2xvcmUxMjM=",
    "BEGIN " + "PRIVATE KEY",
    "client-key" + "-data:",
    "client-certificate" + "-data:",
)
SENSITIVE_FILENAME_ALLOWLIST = {
    "platform/security/sops/.sops.yaml.example",
    "platform/security/sops/encrypted-secret.example.yaml",
}
GOAL_001_SECRET_SCAN_PREFIXES = (
    ".github/",
    "platform/",
)
GOAL_001_SECRET_SCAN_SUFFIXES = (
    ".yaml",
    ".yml",
    ".yaml.example",
    ".yml.example",
)


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def yaml_documents(path: Path) -> list[dict[str, Any]]:
    docs = yaml.safe_load_all(path.read_text(encoding="utf-8"))
    return [doc for doc in docs if isinstance(doc, dict)]


def all_prereq_yaml() -> list[Path]:
    roots = [ROOT / "platform", ROOT / "policies", ROOT / ".github"]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(
                path
                for path in root.rglob("*")
                if path.suffix in {".yaml", ".yml"}
                and not str(path.relative_to(ROOT)).startswith("platform/kong/")
            )
    files.extend(path for path in [ROOT / "mkdocs.yml", ROOT / ".pre-commit-config.yaml"] if path.exists())
    return sorted(set(files))


def is_placeholder(value: str) -> bool:
    upper = value.strip().strip('"').strip("'").upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def decoded_base64(value: str) -> str | None:
    stripped = value.strip().strip('"').strip("'")
    if len(stripped) < 8:
        return None
    try:
        raw = base64.b64decode(stripped, validate=True)
        return raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None


def should_scan_secret_lines(path_text: str) -> bool:
    return path_text.startswith(GOAL_001_SECRET_SCAN_PREFIXES) and path_text.endswith(
        GOAL_001_SECRET_SCAN_SUFFIXES
    )


def is_allowed_sensitive_filename(path_text: str) -> bool:
    return path_text in SENSITIVE_FILENAME_ALLOWLIST or path_text.endswith(".example")


def is_metadata_note_key(key: str) -> bool:
    normalized = key.strip().lower().replace("_", "-")
    return normalized.endswith("-note") or normalized.endswith("note")


def looks_like_kubeconfig(path_text: str, content: str) -> bool:
    if not (
        "kubeconfig" in path_text
        or path_text.startswith(".kube/")
        or path_text.endswith(".kubeconfig")
    ):
        return False
    return all(marker in content for marker in ("clusters:", "contexts:", "current-context:", "users:"))


def check_required_paths(errors: list[str]) -> None:
    for path in REQUIRED_DIRS:
        if not (ROOT / path).is_dir():
            errors.append(f"missing directory: {path}")
    for path in REQUIRED_FILES:
        if not (ROOT / path).is_file():
            errors.append(f"missing file: {path}")
    for namespace in REQUIRED_NAMESPACES:
        path = ROOT / "platform/namespaces" / f"{namespace}.yaml"
        if not path.is_file():
            errors.append(f"missing namespace manifest: {path.relative_to(ROOT)}")


def check_namespace_labels(errors: list[str]) -> None:
    for namespace, owner in REQUIRED_NAMESPACES.items():
        path = ROOT / "platform/namespaces" / f"{namespace}.yaml"
        if not path.is_file():
            continue
        docs = yaml_documents(path)
        if len(docs) != 1:
            errors.append(f"{path.relative_to(ROOT)} must contain one document")
            continue
        doc = docs[0]
        labels = doc.get("metadata", {}).get("labels", {})
        if doc.get("kind") != "Namespace":
            errors.append(f"{path.relative_to(ROOT)} is not a Namespace")
        if doc.get("metadata", {}).get("name") != namespace:
            errors.append(f"{path.relative_to(ROOT)} name mismatch")
        for key, expected in REQUIRED_LABELS.items():
            if labels.get(key) != expected:
                errors.append(f"{namespace} missing label {key}={expected}")
        if labels.get("banklab.konghq.com/owner") != owner:
            errors.append(f"{namespace} missing owner {owner}")


def check_forbidden_kong_resources(errors: list[str]) -> None:
    for path in all_prereq_yaml():
        for doc in yaml_documents(path):
            kind = doc.get("kind")
            if kind in FORBIDDEN_KONG_KINDS:
                errors.append(f"forbidden Kong resource {kind} in {path.relative_to(ROOT)}")


def check_secret_hygiene(errors: list[str]) -> None:
    for path_text in git_files():
        if path_text.startswith("kubespray/"):
            continue
        path = ROOT / path_text
        if not path.is_file():
            continue
        if path.name in {"age.key", "age.txt", ".sops-age-key.txt", "kubeconfig"}:
            errors.append(f"forbidden sensitive filename: {path_text}")
        if path.suffix in {".key", ".pem", ".p12", ".pfx"} and not is_allowed_sensitive_filename(path_text):
            errors.append(f"forbidden sensitive file suffix: {path_text}")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if looks_like_kubeconfig(path_text, content):
            errors.append(f"kubeconfig-like content found in {path_text}")
        for marker in KNOWN_BAD_MARKERS:
            if marker in content:
                errors.append(f"known unsafe secret marker found in {path_text}")
        if not should_scan_secret_lines(path_text):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if not SECRET_KEY_RE.search(key):
                continue
            if is_metadata_note_key(key):
                continue
            stripped = value.strip()
            if not stripped or is_placeholder(stripped):
                continue
            decoded = decoded_base64(stripped)
            if decoded and not is_placeholder(decoded):
                errors.append(f"base64 secret-like value in {path_text}:{line_number}")
            elif stripped.startswith("{{") or stripped.startswith("${"):
                continue
            elif path_text.endswith(".md"):
                continue
            else:
                errors.append(f"plaintext secret-like value in {path_text}:{line_number}")


def check_placeholders(errors: list[str]) -> None:
    app_files = list((ROOT / "platform/gitops/app-of-apps").glob("*.yaml"))
    project_files = list((ROOT / "platform/gitops/projects").glob("*.yaml"))
    for path in app_files + project_files:
        content = path.read_text(encoding="utf-8")
        if "REPLACE_WITH_REPO_URL" not in content:
            errors.append(f"{path.relative_to(ROOT)} must use REPLACE_WITH_REPO_URL")
    metallb_pool = ROOT / "platform/networking/metallb/ip-address-pool.example.yaml"
    if "example-only" not in metallb_pool.read_text(encoding="utf-8"):
        errors.append("MetalLB address pool must be marked example-only")
    sops_example = ROOT / "platform/security/sops/.sops.yaml.example"
    content = sops_example.read_text(encoding="utf-8")
    if "REPLACE_WITH_AGE_PUBLIC_RECIPIENT" not in content:
        errors.append(".sops.yaml.example must use REPLACE_WITH_AGE_PUBLIC_RECIPIENT")


def check_network_policy_baseline(errors: list[str]) -> None:
    kinds_by_file: dict[str, list[str]] = {}
    for path in (ROOT / "platform/networking/network-policies").glob("*.yaml"):
        kinds_by_file[path.name] = [doc.get("kind", "") for doc in yaml_documents(path)]
    for required in [
        "platform-default-deny.yaml",
        "tenants-default-deny.yaml",
        "allow-dns.yaml",
        "allow-gitops-to-managed-namespaces.yaml",
        "allow-observability-scrape-placeholder.yaml",
        "allow-ingress-controller-placeholder.yaml",
    ]:
        if "NetworkPolicy" not in kinds_by_file.get(required, []):
            errors.append(f"{required} must contain a NetworkPolicy")


def main() -> int:
    errors: list[str] = []
    check_required_paths(errors)
    check_namespace_labels(errors)
    check_forbidden_kong_resources(errors)
    check_secret_hygiene(errors)
    check_placeholders(errors)
    check_network_policy_baseline(errors)

    if errors:
        print("Platform prerequisite validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Platform prerequisite validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
