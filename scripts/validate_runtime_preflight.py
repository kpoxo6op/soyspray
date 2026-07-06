#!/usr/bin/env python3
"""Validate the gate-002 runtime preflight package locally."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/gate-002-runtime-preflight.md",
    "docs/architecture/kong-runtime-validation-gate.md",
    "docs/architecture/cluster-mutation-guardrails.md",
    "docs/runbooks/kong-runtime-preflight.md",
    "docs/runbooks/kong-runtime-apply-checklist.md",
    "docs/runbooks/kong-runtime-smoke-checklist.md",
    "docs/runbooks/kong-runtime-rollback-checklist.md",
    "docs/decisions/goal-003-blocked-until-kong-runtime-validation.md",
    "platform/kong/PRE-CLUSTER-APPLY-CHECKLIST.md",
    "platform/kong/CLUSTER-APPLY-REQUEST.md",
    "platform/kong/RUNTIME-VALIDATION-CHECKLIST.md",
    "platform/kong/ROLLBACK-CHECKLIST.md",
    "platform/kong/scripts/require-cluster-mutation-permission.sh",
    "platform/kong/scripts/cluster-readonly-preflight.sh",
    "platform/kong/scripts/kong-readonly-preflight.sh",
    "platform/kong/scripts/generate-kong-apply-plan.sh",
    "scripts/validate_runtime_preflight.py",
    "reports/gate-002-runtime-preflight-summary.md",
]

READONLY_SCRIPTS = [
    "platform/kong/scripts/cluster-readonly-preflight.sh",
    "platform/kong/scripts/kong-readonly-preflight.sh",
]

FORBIDDEN_MUTATION_PATTERNS = [
    r"\bkubectl\s+apply\b",
    r"\bkubectl\s+delete\b",
    r"\bkubectl\s+patch\b",
    r"\bkubectl\s+label\b",
    r"\bkubectl\s+annotate\b",
    r"\bkubectl\s+scale\b",
    r"\bkubectl\s+rollout\s+restart\b",
    r"\bhelm\s+install\b",
    r"\bhelm\s+upgrade\b",
    r"\bhelm\s+uninstall\b",
    r"\bargocd\s+app\s+sync\b",
]

FORBIDDEN_CI_TARGETS = [
    "cluster-readonly-preflight",
    "kong-readonly-preflight",
    "cluster-smoke",
    "cluster-prereq-smoke",
    "kong-install-dry-run",
    "kong-apply",
    "kong-cluster-smoke",
    "kong-route-smoke",
    "kong-rollback",
]

SECRET_NAME_MARKERS = (".env", "id_rsa", "id_ed25519", "kubeconfig", "admin.conf", "auth-profiles.json")
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def check_required_files(errors: list[str]) -> None:
    for path in REQUIRED_FILES:
        full = ROOT / path
        require(full.is_file(), errors, f"missing required file: {path}")
        if full.is_file() and full.suffix in {".md", ".py", ".sh", ".yml", ".yaml"}:
            require(full.read_text(encoding="utf-8").strip() != "", errors, f"required file is empty: {path}")


def target_block(makefile: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", re.M)
    match = pattern.search(makefile)
    return match.group("body") if match else ""


def check_makefile_guards(errors: list[str]) -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    guard = "platform/kong/scripts/require-cluster-mutation-permission.sh"
    for target in ("kong-apply", "kong-rollback"):
        block = target_block(makefile, target)
        require(block, errors, f"missing Makefile target: {target}")
        require(guard in block, errors, f"{target} must call the mutation permission guard")
    for target in (
        "runtime-preflight-local",
        "kong-apply-plan",
        "cluster-readonly-preflight",
        "kong-readonly-preflight",
        "mutation-guard-test",
        "evidence-gate-002-runtime-preflight",
    ):
        require(target_block(makefile, target), errors, f"missing Makefile target: {target}")


def check_readonly_scripts(errors: list[str]) -> None:
    compiled = [re.compile(pattern) for pattern in FORBIDDEN_MUTATION_PATTERNS]
    for path in READONLY_SCRIPTS:
        content = (ROOT / path).read_text(encoding="utf-8")
        require("current-context" in content, errors, f"{path} must print or inspect current context")
        for pattern in compiled:
            require(not pattern.search(content), errors, f"read-only script contains mutating pattern {pattern.pattern}: {path}")


def check_goal_002_state(errors: list[str]) -> None:
    report = (ROOT / "reports/goal-002-summary.md").read_text(encoding="utf-8")
    lowered = report.lower()
    require("status: pass; local-only" in lowered, errors, "goal 002 evidence must remain pass; local-only")
    require("cluster changes performed" in lowered and "none" in lowered, errors, "goal 002 must record no cluster changes")
    require("cluster verification" in lowered and "not run" in lowered, errors, "goal 002 must record cluster verification not run")
    require("no; run cluster apply and smoke tests before goal-003" in lowered, errors, "goal 002 must keep goal 003 blocked")


def check_versions(errors: list[str]) -> None:
    versions = yaml.safe_load((ROOT / "platform/kong/versions.yaml").read_text(encoding="utf-8"))
    require(versions["kong_gateway"]["image_repository"] == "kong", errors, "Kong Gateway repository must stay kong")
    require(versions["kong_gateway"]["image_tag"] == "3.9.3", errors, "Kong Gateway tag must stay 3.9.3")
    require(versions["kong_ingress_controller"]["image_tag"] == "3.5.10", errors, "KIC tag must stay 3.5.10")
    require(versions["gateway_api"]["version"] == "v1.3.0", errors, "Gateway API must stay v1.3.0")
    validator = (ROOT / "scripts/validate_kong_baseline.py").read_text(encoding="utf-8")
    require("check_kic_gateway_api_compatibility" in validator, errors, "KIC/Gateway API compatibility validation must remain present")
    require("minor <= 3" in validator, errors, "KIC 3.5.x must reject Gateway API versions above v1.3.x")


def check_goal003_blocked(errors: list[str]) -> None:
    decision = (ROOT / "docs/decisions/goal-003-blocked-until-kong-runtime-validation.md").read_text(encoding="utf-8").lower()
    normalized = re.sub(r"\s+", " ", decision)
    require("blocked until goal-002 runtime validation passes" in normalized, errors, "goal 003 block decision must be explicit")
    require(not (ROOT / "soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md").exists(), errors, "goal 003 body must not be created in this gate")


def check_ci_cluster_free(errors: list[str]) -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    require("make runtime-preflight-local" in ci, errors, "CI must run runtime-preflight-local")
    require("make mutation-guard-test" in ci, errors, "CI must run mutation-guard-test")
    for target in FORBIDDEN_CI_TARGETS:
        pattern = rf"run:\s+make\s+{re.escape(target)}(?:\s|$)"
        require(not re.search(pattern, ci), errors, f"CI must not run {target}")


def has_secret_like_name(path: str) -> bool:
    name = Path(path).name.lower()
    lower_path = path.lower()
    return (
        name in SECRET_NAME_MARKERS
        or any(name.endswith(suffix) for suffix in SECRET_SUFFIXES)
        or lower_path.endswith("/.kube/config")
    )


def check_no_sensitive_files(errors: list[str]) -> None:
    unsafe = [
        path
        for path in git_files()
        if (ROOT / path).is_file()
        and not path.startswith("kubespray/")
        and has_secret_like_name(path)
    ]
    require(not unsafe, errors, "secret-like file names are present: " + ", ".join(sorted(unsafe)))


def check_evidence_structure(errors: list[str]) -> None:
    report = (ROOT / "reports/gate-002-runtime-preflight-summary.md").read_text(encoding="utf-8")
    for term in (
        "Gate: gate-002-runtime-preflight",
        "Cluster changes performed:",
        "Secrets created:",
        "Kong runtime applied:",
        "Kong route smoke passed:",
        "Admin API externally exposed:",
        "Next assigned gate:",
    ):
        require(term in report, errors, f"runtime preflight evidence missing term: {term}")


def validate() -> list[str]:
    errors: list[str] = []
    check_required_files(errors)
    check_makefile_guards(errors)
    check_readonly_scripts(errors)
    check_goal_002_state(errors)
    check_versions(errors)
    check_goal003_blocked(errors)
    check_ci_cluster_free(errors)
    check_no_sensitive_files(errors)
    check_evidence_structure(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Runtime preflight validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Runtime preflight validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
