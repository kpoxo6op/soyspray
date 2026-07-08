#!/usr/bin/env python3
"""Validate the goal-000 repository foundation."""

from __future__ import annotations

import subprocess
import sys
import base64
import binascii
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "docs/architecture",
    "docs/adr",
    "docs/onboarding",
    "docs/runbooks",
    "docs/decisions",
    "platform/gitops",
    "platform/kong",
    "platform/identity",
    "platform/observability",
    "platform/security",
    "platform/networking",
    "tenants/tenant-template",
    "apis/api-template/tests",
    "policies/conftest",
    "policies/examples",
    "tests/unit",
    "tests/policy",
    "tests/integration",
    "tests/fixtures",
    "reports",
]

REQUIRED_FILES = [
    "README.md",
    "ROADMAP.md",
    "Makefile",
    ".gitignore",
    ".editorconfig",
    ".pre-commit-config.yaml",
    "CODEOWNERS",
    ".github/workflows/ci.yml",
    "docs/index.md",
    "docs/architecture/README.md",
    "docs/architecture/platform-principles.md",
    "docs/architecture/oss-vs-enterprise.md",
    "docs/architecture/operating-model.md",
    "docs/architecture/testing-strategy.md",
    "docs/adr/README.md",
    "docs/adr/adr-template.md",
    "docs/adr/0001-platform-direction.md",
    "docs/onboarding/README.md",
    "docs/onboarding/api-onboarding-template.md",
    "docs/runbooks/README.md",
    "docs/runbooks/runbook-template.md",
    "docs/decisions/README.md",
    "platform/README.md",
    "platform/gitops/README.md",
    "platform/kong/README.md",
    "platform/identity/README.md",
    "platform/observability/README.md",
    "platform/security/README.md",
    "platform/networking/README.md",
    "tenants/README.md",
    "tenants/tenant-template/README.md",
    "apis/README.md",
    "apis/api-template/README.md",
    "apis/api-template/openapi.yaml",
    "apis/api-template/ownership.yaml",
    "apis/api-template/tests/README.md",
    "policies/README.md",
    "policies/conftest/README.md",
    "policies/conftest/placeholder.rego",
    "policies/examples/valid-api-metadata.yaml",
    "policies/examples/invalid-api-metadata.yaml",
    "tests/README.md",
    "tests/unit/README.md",
    "tests/unit/test_repo_foundation.py",
    "tests/policy/README.md",
    "tests/policy/test_policy_placeholders.py",
    "tests/integration/README.md",
    "tests/fixtures/README.md",
    "scripts/README.md",
    "scripts/validate_repo.py",
    "scripts/generate_evidence_report.py",
    "reports/README.md",
    "reports/goal-000-summary.md",
    "mkdocs.yml",
]

FOUNDATION_PREFIXES = (
    ".github/",
    "docs/",
    "platform/",
    "tenants/",
    "apis/",
    "policies/",
    "tests/",
    "reports/",
)

FOUNDATION_FILES = {
    "README.md",
    "ROADMAP.md",
    "Makefile",
    ".gitignore",
    ".editorconfig",
    ".pre-commit-config.yaml",
    "CODEOWNERS",
    "requirements-dev.txt",
    "mkdocs.yml",
    "scripts/validate_repo.py",
    "scripts/generate_evidence_report.py",
}

SECRET_NAME_MARKERS = (
    ".env",
    "id_rsa",
    "id_ed25519",
    "kubeconfig",
    "admin.conf",
)

SECRET_SUFFIXES = (
    ".key",
    ".pem",
    ".p12",
    ".pfx",
)

SECRET_KEY_RE = re.compile(r"(password|secret|token|private[_-]?key|access[_-]?key)", re.I)

KNOWN_SECRET_MARKERS = (
    "book" + "lore123",
    "password: " + "immich",
    "Ym9v" + "a2xvcmUxMjM=",
    "client-key" + "-data:",
    "client-certificate" + "-data:",
)

PLACEHOLDER_MARKERS = (
    "",
    "CHANGE_ME",
    "REPLACE_ME",
    "PLACEHOLDER",
    "EXAMPLE",
    "DUMMY",
    "NONE",
    "N/A",
    "NOT RUN",
    "NO",
    "FALSE",
    "TRUE",
    "PENDING",
    "{{",
    "$",
)

REQUIRED_CONTENT = {
    "README.md": ["Kong OSS bank-lab", "nothing deployed without tests"],
    "ROADMAP.md": ["goal-000", "Kong OSS baseline", "day-2 operations"],
    "docs/architecture/oss-vs-enterprise.md": [
        "Kong RBAC",
        "Kong Workspaces",
        "Kong OIDC plugin",
        "Request Validator plugin",
        "MTLS Auth plugin",
        "Developer Portal",
        "Audit logs",
    ],
    "docs/architecture/operating-model.md": [
        "Platform Admin",
        "API Team Maintainer",
        "Security Reviewer",
        "Read-Only Auditor",
    ],
    "docs/adr/0001-platform-direction.md": [
        "Use Kong OSS as the baseline",
        "Use Kubernetes as the runtime",
        "Use GitOps as the configuration model",
    ],
}


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def is_foundation_file(path: str) -> bool:
    return path in FOUNDATION_FILES or path.startswith(FOUNDATION_PREFIXES)


def has_secret_like_name(path: str) -> bool:
    name = Path(path).name.lower()
    lower_path = path.lower()
    return (
        name in SECRET_NAME_MARKERS
        or any(name.endswith(suffix) for suffix in SECRET_SUFFIXES)
        or lower_path.endswith("/.kube/config")
        or lower_path.endswith("/auth-profiles.json")
    )


def check_required_paths(errors: list[str]) -> None:
    for path in REQUIRED_DIRS:
        if not (ROOT / path).is_dir():
            errors.append(f"missing required directory: {path}")
    for path in REQUIRED_FILES:
        if not (ROOT / path).is_file():
            errors.append(f"missing required file: {path}")


def check_required_content(errors: list[str]) -> None:
    for path, terms in REQUIRED_CONTENT.items():
        content = (ROOT / path).read_text(encoding="utf-8").lower()
        missing = [term for term in terms if term.lower() not in content]
        if missing:
            errors.append(f"{path} missing required terms: {', '.join(missing)}")
    for path in REQUIRED_FILES:
        full_path = ROOT / path
        if full_path.suffix in {".md", ".yaml", ".yml", ".rego"}:
            if full_path.read_text(encoding="utf-8").strip() == "":
                errors.append(f"required file is empty: {path}")


def check_foundation_safety(errors: list[str]) -> None:
    unsafe = [
        path
        for path in git_files()
        if is_foundation_file(path) and has_secret_like_name(path)
    ]
    if unsafe:
        errors.append(
            "secret-like file names are present in goal-000 foundation files: "
            + ", ".join(sorted(unsafe))
        )

    kong_readme = ROOT / "platform/kong/README.md"
    if kong_readme.is_file() and "Kong OSS" not in kong_readme.read_text(encoding="utf-8"):
        errors.append("platform/kong/README.md must document the Kong OSS boundary")


def is_placeholder(value: str) -> bool:
    stripped = value.strip().strip('"').strip("'")
    upper = stripped.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def decode_base64(value: str) -> str | None:
    stripped = value.strip().strip('"').strip("'")
    if len(stripped) < 8:
        return None
    try:
        decoded = base64.b64decode(stripped, validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None


def is_kubeconfig_content(content: str) -> bool:
    markers = (
        "api" + "Version:",
        "clusters" + ":",
        "contexts" + ":",
        "current" + "-context:",
        "users" + ":",
    )
    return all(
        marker in content
        for marker in markers
    )


def check_repo_secret_hygiene(errors: list[str]) -> None:
    files = [
        path
        for path in git_files()
        if (ROOT / path).is_file()
        and not path.startswith("kubespray/")
        and not path.startswith("soydocs/kong-bank-lab/goals/goal-000-repo-foundation.md")
    ]

    unsafe_names = [path for path in files if has_secret_like_name(path)]
    if unsafe_names:
        errors.append(
            "secret-like file names are present in tracked/unignored files: "
            + ", ".join(sorted(unsafe_names))
        )

    for path in files:
        full_path = ROOT / path
        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if is_kubeconfig_content(content):
            errors.append(f"kubeconfig-like content found in {path}")

        for marker in KNOWN_SECRET_MARKERS:
            if marker in content:
                errors.append(f"known plaintext/default secret marker found in {path}")

        for lineno, line in enumerate(content.splitlines(), start=1):
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            if not SECRET_KEY_RE.search(key):
                continue
            value = raw_value.strip()
            if not value or is_placeholder(value):
                continue
            decoded = decode_base64(value)
            if decoded is not None and is_placeholder(decoded):
                continue
            if decoded is not None:
                errors.append(
                    f"base64 secret-like value found in {path}:{lineno} ({key.strip()})"
                )
                continue
            if value.startswith("{{") or value.startswith("${"):
                continue
            errors.append(f"plaintext secret-like value found in {path}:{lineno}")


def main() -> int:
    errors: list[str] = []
    check_required_paths(errors)
    check_required_content(errors)
    check_foundation_safety(errors)
    check_repo_secret_hygiene(errors)

    if errors:
        print("Repository foundation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository foundation validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
