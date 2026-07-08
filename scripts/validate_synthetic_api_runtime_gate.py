#!/usr/bin/env python3
"""Validate the goal-003 synthetic API runtime gate package locally."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/gate-003-synthetic-api-runtime-apply-and-smoke.md",
    "docs/runbooks/synthetic-api-runtime-apply-and-smoke.md",
    "docs/runbooks/synthetic-api-runtime-failure.md",
    "docs/runbooks/synthetic-api-runtime-verification-evidence.md",
    "docs/decisions/goal-003-runtime-approval.md",
    "platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md",
    "platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md",
    "platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md",
    "platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md",
    "platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh",
    "platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh",
    "platform/kong/synthetic-apis/scripts/verify-goal003-runtime-ready.sh",
    "scripts/render_synthetic_api_tenant_namespaces.py",
    "reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md",
]

RUNTIME_RESULT_FILES = [
    "platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md",
    "platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md",
    "platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md",
    "platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md",
    "reports/synthetic-api-runtime-evidence.md",
    "reports/synthetic-api-route-smoke-results.md",
    "reports/synthetic-api-negative-test-results.md",
]

FORBIDDEN_CI_TARGETS = [
    "synthetic-api-install-dry-run",
    "synthetic-api-tenant-namespaces-dry-run",
    "synthetic-api-tenant-namespaces-apply",
    "synthetic-api-apply",
    "synthetic-api-smoke",
    "synthetic-api-negative-test",
    "synthetic-api-rollback",
    "synthetic-api-runtime-ready",
    "goal003-runtime-ready",
]

SECRET_NAME_MARKERS = (".env", "id_rsa", "id_ed25519", "kubeconfig", "admin.conf", "auth-profiles.json")
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


def file_text(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in result.stdout.splitlines() if line]


def status_line(relative: str) -> str:
    for line in file_text(relative).splitlines():
        if line.startswith("Status:"):
            return line.removeprefix("Status:").strip()
    return "missing"


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def target_block(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
    return match.group("body") if match else ""


def appears_in_order(text: str, markers: tuple[str, ...]) -> bool:
    offset = 0
    for marker in markers:
        index = text.find(marker, offset)
        if index == -1:
            return False
        offset = index + len(marker)
    return True


def runtime_approved() -> bool:
    return (
        status_line("docs/decisions/goal-003-runtime-approval.md") == "approved"
        and status_line("reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md") == "pass; runtime-verified"
    )


def check_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        require((ROOT / relative).is_file(), errors, f"missing required runtime gate file: {relative}")


def check_result_file_states(errors: list[str]) -> None:
    required_states = ("not run", "pass", "fail", "blocked", "partial")
    for relative in RUNTIME_RESULT_FILES:
        text = file_text(relative).lower()
        require("status:" in text, errors, f"{relative} must include Status")
        for state in required_states:
            require(state in text, errors, f"{relative} must support state: {state}")


def check_approval_state(errors: list[str]) -> None:
    decision = file_text("docs/decisions/goal-003-runtime-approval.md")
    summary = file_text("reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md")
    if runtime_approved():
        for relative in RUNTIME_RESULT_FILES:
            require(status_line(relative) == "pass", errors, f"{relative} must pass before runtime approval")
        return
    require("Status: pending" in decision, errors, "runtime approval decision must remain pending before runtime pass")
    for marker in (
        "Status: pending explicit cluster mutation permission",
        "Mutation permission granted: no",
        "Cluster changes performed: none",
        "Runtime verification: not run",
        "Runtime approval: pending",
        "Ready for goal 004: no",
    ):
        require(marker in summary, errors, f"gate summary missing pending marker: {marker}")


def check_makefile_and_scripts(errors: list[str]) -> None:
    makefile = file_text("Makefile")
    ci = file_text(".github/workflows/ci.yml")
    guard = "require-cluster-mutation-permission.sh"
    for target in ("synthetic-api-tenant-namespaces-apply", "synthetic-api-apply", "synthetic-api-rollback"):
        block = target_block(makefile, target)
        require(block, errors, f"missing Makefile target: {target}")
        require(guard in block, errors, f"{target} must call mutation guard")
    for target in (
        "render-synthetic-api-tenant-namespaces",
        "synthetic-api-tenant-namespaces-dry-run",
        "validate-synthetic-api-runtime-gate",
        "evidence-gate-003-synthetic-api-runtime",
        "goal003-runtime-ready",
    ):
        require(target_block(makefile, target), errors, f"missing Makefile target: {target}")
    runtime_script = file_text("platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh")
    require(guard in runtime_script, errors, "runtime apply-and-smoke script must call mutation guard")
    require(
        appears_in_order(
            runtime_script,
            (
                "make synthetic-api-tenant-namespaces-dry-run",
                "make synthetic-api-tenant-namespaces-apply",
                "make synthetic-api-install-dry-run",
            ),
        ),
        errors,
        "runtime apply-and-smoke script must bootstrap tenant namespaces before synthetic API dry-run",
    )
    require("make synthetic-api-apply" in runtime_script, errors, "runtime apply-and-smoke script must use Makefile apply target")
    require("make synthetic-api-smoke" in runtime_script, errors, "runtime apply-and-smoke script must use Makefile smoke target")
    require("make synthetic-api-negative-test" in runtime_script, errors, "runtime apply-and-smoke script must use Makefile negative target")
    require("make validate-synthetic-api-runtime-gate" in ci, errors, "CI must run local runtime gate validation")
    for target in FORBIDDEN_CI_TARGETS:
        require(not re.search(rf"run:\s+make\s+{re.escape(target)}(?:\s|$)", ci), errors, f"CI must not run {target}")
    require("synthetic-api-runtime-apply-and-smoke.sh" not in ci, errors, "CI must not run runtime apply script")


def check_goal004_block(errors: list[str]) -> None:
    if runtime_approved():
        return
    require(not (ROOT / "soydocs/kong-bank-lab/goals/goal-004-auth-rate-limit-security.md").exists(), errors, "goal 004 body must not exist before goal003 runtime approval")
    require("Ready for next goal: no" in file_text("reports/goal-003-summary.md"), errors, "goal 003 evidence must keep next goal blocked")


def has_secret_like_name(path: str) -> bool:
    name = Path(path).name.lower()
    lower_path = path.lower()
    return name in SECRET_NAME_MARKERS or any(name.endswith(suffix) for suffix in SECRET_SUFFIXES) or lower_path.endswith("/.kube/config")


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
    check_result_file_states(errors)
    check_approval_state(errors)
    check_makefile_and_scripts(errors)
    check_goal004_block(errors)
    check_no_sensitive_files(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Synthetic API runtime gate validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Synthetic API runtime gate validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
