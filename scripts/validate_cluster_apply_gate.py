#!/usr/bin/env python3
"""Validate the local package for gate-002 cluster apply and smoke."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/gate-002-cluster-apply-and-smoke.md",
    "docs/runbooks/kong-cluster-apply-and-smoke.md",
    "docs/runbooks/kong-cluster-apply-failure.md",
    "docs/runbooks/kong-runtime-verification-evidence.md",
    "docs/decisions/goal-002-runtime-approval.md",
    "platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md",
    "platform/kong/CLUSTER-SMOKE-RESULTS.md",
    "platform/kong/ROUTE-SMOKE-RESULTS.md",
    "platform/kong/ADMIN-API-EXPOSURE-RESULTS.md",
    "platform/kong/scripts/kong-cluster-apply-and-smoke.sh",
    "platform/kong/scripts/collect-kong-runtime-evidence.sh",
    "platform/kong/scripts/verify-goal002-runtime-ready.sh",
    "scripts/validate_cluster_apply_gate.py",
    "reports/gate-002-cluster-apply-and-smoke-summary.md",
]

RESULT_FILES = [
    "platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md",
    "platform/kong/CLUSTER-SMOKE-RESULTS.md",
    "platform/kong/ROUTE-SMOKE-RESULTS.md",
    "platform/kong/ADMIN-API-EXPOSURE-RESULTS.md",
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

MUTATING_PATTERNS = [
    r"\bmake\s+kong-apply\b",
    r"\bmake\s+kong-rollback\b",
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


def file_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def runtime_approved_from_files() -> bool:
    required = {
        "docs/decisions/goal-002-runtime-approval.md": ("Status: approved",),
        "reports/gate-002-cluster-apply-and-smoke-summary.md": (
            "Status: pass; runtime-verified",
            "Kong runtime applied: yes",
            "Kong route smoke passed: yes",
            "Admin API externally exposed: no",
            "Runtime approval: approved",
            "Ready for goal 003: yes",
        ),
        "reports/goal-002-summary.md": ("runtime-verified",),
    }
    for relative in RESULT_FILES:
        required[relative] = ("Status: pass",)

    return all(all(marker in file_text(relative) for marker in markers) for relative, markers in required.items())


def target_block(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
    return match.group("body") if match else ""


def check_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        require(path.is_file(), errors, f"missing required file: {relative}")
        if path.is_file() and path.suffix in {".md", ".sh", ".py"}:
            require(path.read_text(encoding="utf-8").strip() != "", errors, f"empty required file: {relative}")


def check_mutation_guard(errors: list[str]) -> None:
    guard = ROOT / "platform/kong/scripts/require-cluster-mutation-permission.sh"
    require(guard.is_file(), errors, "mutation guard script is missing")
    script = (ROOT / "platform/kong/scripts/kong-cluster-apply-and-smoke.sh").read_text(encoding="utf-8")
    guard_call = "platform/kong/scripts/require-cluster-mutation-permission.sh"
    require(guard_call in script, errors, "cluster apply script must call mutation guard")
    guard_index = script.find(guard_call)
    mutation_indexes = [
        match.start()
        for pattern in MUTATING_PATTERNS
        for match in re.finditer(pattern, script)
    ]
    if mutation_indexes:
        require(guard_index != -1 and guard_index < min(mutation_indexes), errors, "mutation guard must appear before mutating commands")

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("kong-apply", "kong-rollback"):
        block = target_block(makefile, target)
        require(guard_call in block, errors, f"{target} must remain guarded")
    for target in ("validate-cluster-apply-gate", "evidence-gate-002-cluster-apply-and-smoke", "goal002-runtime-ready"):
        require(target_block(makefile, target), errors, f"missing Makefile target: {target}")


def check_ci_cluster_free(errors: list[str]) -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    require("make validate-cluster-apply-gate" in ci, errors, "CI must run validate-cluster-apply-gate")
    for target in FORBIDDEN_CI_TARGETS:
        pattern = rf"run:\s+make\s+{re.escape(target)}(?:\s|$)"
        require(not re.search(pattern, ci), errors, f"CI must not run {target}")
    require("kong-cluster-apply-and-smoke.sh" not in ci, errors, "CI must not run cluster apply script")


def check_runtime_approval_state(errors: list[str]) -> None:
    decision = file_text("docs/decisions/goal-002-runtime-approval.md")
    summary = file_text("reports/gate-002-cluster-apply-and-smoke-summary.md")

    if "Status: approved" in decision:
        require(runtime_approved_from_files(), errors, "runtime approval requires all runtime evidence files to show pass")
        return

    require("Status: pending" in decision, errors, "runtime approval decision must be pending or approved")
    for expected in (
        "Status: pending explicit cluster mutation permission",
        "Explicit mutation permission required: yes",
        "Mutation permission granted: no",
        "Cluster changes performed: none",
        "Kong runtime applied: no",
        "Kong route smoke passed: no",
        "Runtime approval: pending",
        "Ready for goal 003: no",
    ):
        require(expected in summary, errors, f"cluster apply evidence missing default: {expected}")


def check_result_files(errors: list[str]) -> None:
    approved = runtime_approved_from_files()
    for relative in RESULT_FILES:
        content = file_text(relative)
        expected_status = "Status: pass" if approved else "Status: not run"
        require(expected_status in content, errors, f"{relative} must contain {expected_status}")
        for state in ("not run", "pass", "fail", "blocked"):
            require(state in content.lower() or relative.endswith("SUMMARY.md"), errors, f"{relative} should support state: {state}")


def check_goal003_state(errors: list[str]) -> None:
    goal003_exists = (ROOT / "soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md").exists()
    if goal003_exists:
        require(runtime_approved_from_files(), errors, "goal 003 body requires approved goal 002 runtime evidence")
        return

    decision = file_text("docs/decisions/goal-003-blocked-until-kong-runtime-validation.md").lower()
    normalized = re.sub(r"\s+", " ", decision)
    if not runtime_approved_from_files():
        require("blocked until goal-002 runtime validation passes" in normalized, errors, "goal 003 block decision must remain explicit")


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


def validate() -> list[str]:
    errors: list[str] = []
    check_required_files(errors)
    check_mutation_guard(errors)
    check_ci_cluster_free(errors)
    check_runtime_approval_state(errors)
    check_result_files(errors)
    check_goal003_state(errors)
    check_no_sensitive_files(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Cluster apply gate validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Cluster apply gate validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
