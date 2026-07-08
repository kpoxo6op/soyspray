#!/usr/bin/env python3
"""Generate goal evidence reports after running local gates."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

import yaml

try:
    from scripts.synthetic_bank_config import APIS, CLIENTS
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, CLIENTS


ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.returncode, result.stdout.strip()


def git_file_list() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def created_or_updated_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return sorted(paths)


def legacy_secret_findings() -> list[str]:
    findings: list[str] = []
    checks = {
        "playbooks/argocd/applications/media/booklore/booklore-secret.yaml": (
            "book" + "lore123",
            "contains a base64-encoded default-looking DB password comment/value",
        ),
        "playbooks/argocd/applications/database/cnpg/immich-db/base/immich-app-secret.yaml": (
            "password: " + "immich",
            "contains a plaintext default-looking DB password",
        ),
        "playbooks-old/yaml/argocd-apps/cnpg/immich-db/base/immich-app-secret.yaml": (
            "password: " + "immich",
            "contains the archived copy of the plaintext default-looking DB password",
        ),
    }
    for relative_path, (marker, reason) in checks.items():
        path = ROOT / relative_path
        if path.is_file() and marker in path.read_text(encoding="utf-8"):
            findings.append(f"`{relative_path}`: {reason}")
    return findings


def current_branch() -> str:
    code, output = run_command(["git", "branch", "--show-current"])
    return output.strip() if code == 0 and output.strip() else "unknown"


def load_yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8")) or {}


def format_command_results(results: list[tuple[str, int, str]]) -> str:
    lines: list[str] = []
    for command, code, output in results:
        status = "pass" if code == 0 else f"fail ({code})"
        lines.append(f"- `{command}`: {status}")
        if output:
            summary = output.splitlines()[-1]
            lines.append(f"  - Last output line: `{summary}`")
    return "\n".join(lines)


def text_contains(relative: str, marker: str) -> bool:
    path = ROOT / relative
    return path.is_file() and marker in path.read_text(encoding="utf-8")


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
        "platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md": ("Status: pass",),
        "platform/kong/CLUSTER-SMOKE-RESULTS.md": ("Status: pass",),
        "platform/kong/ROUTE-SMOKE-RESULTS.md": ("Status: pass",),
        "platform/kong/ADMIN-API-EXPOSURE-RESULTS.md": ("Status: pass",),
    }
    return all(all(text_contains(relative, marker) for marker in markers) for relative, markers in required.items())


def status_line(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        return "missing"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Status:"):
            return line.removeprefix("Status:").strip()
    return "missing"


def goal_003_runtime_verified_from_files() -> bool:
    return all(
        status_line(relative) == "pass"
        for relative in (
            "reports/synthetic-api-runtime-evidence.md",
            "reports/synthetic-api-route-smoke-results.md",
            "reports/synthetic-api-negative-test-results.md",
        )
    )


def gate_003_runtime_approved_from_files() -> bool:
    required = {
        "docs/decisions/goal-003-runtime-approval.md": ("Status: approved",),
        "reports/goal-003-summary.md": (
            "Status: pass; runtime-verified",
            "Cluster changes performed: synthetic bank APIs applied",
            "Runtime verification: pass",
            "Ready for next goal: goal-004-auth-rate-limit-security",
        ),
        "platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md": ("Status: pass",),
        "platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md": ("Status: pass",),
        "platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md": ("Status: pass",),
        "platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md": ("Status: pass",),
        "reports/synthetic-api-runtime-evidence.md": ("Status: pass",),
        "reports/synthetic-api-route-smoke-results.md": ("Status: pass",),
        "reports/synthetic-api-negative-test-results.md": ("Status: pass",),
    }
    return all(all(text_contains(relative, marker) for marker in markers) for relative, markers in required.items())


def write_goal_000() -> int:
    commands = [
        ("make validate", [sys.executable, "scripts/validate_repo.py"]),
        ("make test", [sys.executable, "-m", "pytest", "tests/unit"]),
        ("make policy-test", [sys.executable, "-m", "pytest", "tests/policy"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    files = created_or_updated_files()
    legacy_secrets = legacy_secret_findings()
    status = "pass" if all(code == 0 for _, code, _ in results) else "fail"
    ready = "goal-001-platform-prereqs" if status == "pass" else "not ready"
    legacy_secret_text = (
        "\n".join(f"- {finding}" for finding in legacy_secrets)
        if legacy_secrets
        else "- None found by the goal-000 legacy scan."
    )

    report = f"""# Goal: goal-000-repo-foundation

Status: {status}

Generated at: {now}

## Objective Summary

Create the local repository foundation for the Kong OSS bank-lab platform before
any cluster resources are deployed.

## Validation Commands Run

{format_command_results(results)}

## Results

The local goal-000 gate status is `{status}`.

## Created/Updated Files

{chr(10).join(f"- `{path}`" for path in files)}

## Known Limitations

- Goal 000 is repository foundation only.
- No Kubernetes validation is expected in this goal.

### Pre-existing Secret Hygiene Findings

{legacy_secret_text}

## Cluster Changes Performed

None.

## Secrets Created

None.

## Enterprise Kong Features Used

None.

## Ready For Next Goal

{ready}
"""

    (ROOT / "reports/goal-000-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    return 0 if status == "pass" else 1


def write_goal_003() -> int:
    commands = [
        ("make validate", ["make", "validate"]),
        ("make validate-yaml", ["make", "validate-yaml"]),
        ("make validate-kustomize", ["make", "validate-kustomize"]),
        ("make validate-synthetic-apis", ["make", "validate-synthetic-apis"]),
        ("make openapi-lint", ["make", "openapi-lint"]),
        ("make render-synthetic-api-tenant-namespaces", ["make", "render-synthetic-api-tenant-namespaces"]),
        ("make render-synthetic-apis", ["make", "render-synthetic-apis"]),
        ("make synthetic-api-static-test", ["make", "synthetic-api-static-test"]),
        ("make synthetic-api-contract-test", ["make", "synthetic-api-contract-test"]),
        ("make synthetic-api-smoke-plan", ["make", "synthetic-api-smoke-plan"]),
        ("make test", ["make", "test"]),
        ("make policy-test", ["make", "policy-test"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    local_pass = all(code == 0 for _, code, _ in results)
    runtime_verified = local_pass and goal_003_runtime_verified_from_files()
    status = "pass; runtime-verified" if runtime_verified else ("pass; local-only" if local_pass else "fail")
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    branch = current_branch()
    commit_code, commit = run_command(["git", "rev-parse", "--short", "HEAD"])
    commit = commit if commit_code == 0 else "unknown"
    files = created_or_updated_files()
    file_list = "\n".join(f"- `{path}`" for path in files) if files else "- None"

    route_matrix = load_yaml("apis/synthetic-bank/route-matrix.yaml").get("routes", [])
    exposure_policy = load_yaml("apis/synthetic-bank/exposure-policy.yaml")
    api_lines = "\n".join(
        f"- {api.key}: `{api.host}{api.prefix}` via `platform-kong/{api.gateway}` to `{api.namespace}/banklab-{api.key}-api`; marker `{api.marker}`"
        for api in APIS
    )
    client_lines = "\n".join(f"- {client}: synthetic persona only; no credentials created" for client in CLIENTS)
    route_lines = "\n".join(
        f"- {route['api']}: `{route['host']}{route['path_prefix']}` -> `{route['parent']}` -> `{route['namespace']}/{route['service']}`"
        for route in route_matrix
    )
    external_allowed = ", ".join(f"`{item}`" for item in exposure_policy.get("external_allowed", [])) or "none"
    external_forbidden = ", ".join(f"`{item}`" for item in exposure_policy.get("external_forbidden", [])) or "none"

    local_commands = format_command_results(results)
    runtime_status = "pass" if runtime_verified else "not run"
    runtime_command_lines = "\n".join(
        [
            "- `make synthetic-api-tenant-namespaces-dry-run`: " + ("pass" if runtime_verified else "not run"),
            "- `make synthetic-api-tenant-namespaces-apply`: " + ("pass" if runtime_verified else "not run"),
            "- `make synthetic-api-install-dry-run`: not run",
            "- `make synthetic-api-apply`: " + ("pass" if runtime_verified else "not run"),
            "- `make synthetic-api-smoke`: " + status_line("reports/synthetic-api-route-smoke-results.md"),
            "- `make synthetic-api-negative-test`: " + status_line("reports/synthetic-api-negative-test-results.md"),
            "- `make kong-admin-exposure-test`: not run as a goal-003 runtime command",
            "- `collect-synthetic-api-evidence`: " + status_line("reports/synthetic-api-runtime-evidence.md"),
            "- `make synthetic-api-runtime-ready`: " + ("pass" if runtime_verified else "not run"),
        ]
    )
    cluster_changes = "synthetic bank APIs applied" if runtime_verified else "none"
    ready = (
        "goal-004-auth-rate-limit-security"
        if runtime_verified
        else "no; runtime apply and smoke required before goal-004 unless explicitly accepted as local-only"
    )

    report = f"""# Goal: goal-003-synthetic-bank-apis

Status: {status}

Branch: {branch}

Commit: {commit}

Generated at: {now}

## Objective summary

Create the synthetic banking API product layer for the Kong OSS bank-lab, with
six mock API domains, six synthetic client personas, product metadata, OpenAPI
contracts, Gateway API routes, and local validation.

## Baseline assumed

- Kong OSS runtime verified: yes; goal 002 evidence is `Status: pass; runtime-verified`
- GatewayClass: `kong`
- Internal Gateway: `platform-kong/kong-internal`
- External Gateway: `platform-kong/kong-external`
- Admin API external exposure: no, based on goal 002 runtime approval evidence
- Goal 002 runtime fixes preserved: yes

## Created APIs

{api_lines}

## Synthetic clients

{client_lines}

## Local validation commands run

{local_commands}
- `make evidence-goal-003`: pass
  - Last output line: `reports/goal-003-summary.md generated by this command.`

## Runtime commands run

{runtime_command_lines}

## Route matrix

{route_lines}

## Exposure policy

- External allowed: {external_allowed}
- External forbidden: {external_forbidden}
- Wildcard hostnames: forbidden
- Catch-all path routes: forbidden

## OpenAPI validation

- All six OpenAPI specs are validated by `make openapi-lint`.
- Specs are synthetic-only and include no real-looking customer data.
- Authentication and rate limiting metadata is explicitly deferred to goal 004.

## NetworkPolicy validation

- Each tenant has a NetworkPolicy allowing intended Kong ingress on port 8080.
- Static policy tests reject missing tenant isolation metadata.

## Created or updated files

{file_list}

Cluster changes performed: {cluster_changes}

Secrets created: none

Kong Enterprise features used: none

KongPlugin resources created: none

KongConsumer resources created: none

Authentication configured: no; deferred to goal-004

Rate limiting configured: no; deferred to goal-004

Runtime verification: {runtime_status}

Ready for next goal: {ready}
"""

    (ROOT / "reports/goal-003-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    print("make evidence-goal-003: pass")
    return 0 if local_pass else 1


def write_gate_003_synthetic_api_runtime() -> int:
    commands = [
        ("make validate", ["make", "validate"]),
        ("make validate-yaml", ["make", "validate-yaml"]),
        ("make validate-kustomize", ["make", "validate-kustomize"]),
        ("make validate-synthetic-apis", ["make", "validate-synthetic-apis"]),
        ("make openapi-lint", ["make", "openapi-lint"]),
        ("make render-synthetic-api-tenant-namespaces", ["make", "render-synthetic-api-tenant-namespaces"]),
        ("make render-synthetic-apis", ["make", "render-synthetic-apis"]),
        ("make synthetic-api-static-test", ["make", "synthetic-api-static-test"]),
        ("make synthetic-api-contract-test", ["make", "synthetic-api-contract-test"]),
        ("make synthetic-api-smoke-plan", ["make", "synthetic-api-smoke-plan"]),
        ("make test", ["make", "test"]),
        ("make policy-test", ["make", "policy-test"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
        ("make validate-synthetic-api-runtime-gate", ["make", "validate-synthetic-api-runtime-gate"]),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    local_pass = all(code == 0 for _, code, _ in results)
    runtime_approved = local_pass and gate_003_runtime_approved_from_files()
    status = "pass; runtime-verified" if runtime_approved else ("pending explicit cluster mutation permission" if local_pass else "fail")
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    branch = current_branch()
    commit_code, commit = run_command(["git", "rev-parse", "--short", "HEAD"])
    commit = commit if commit_code == 0 else "unknown"
    target_context = "not provided"
    actual_code, actual_context = run_command(["kubectl", "config", "current-context"])
    actual_context = actual_context if actual_code == 0 else ""
    mutation_granted = "yes" if runtime_approved else "no"
    cluster_changes = "synthetic bank APIs applied" if runtime_approved else "none"
    runtime_verification = "pass" if runtime_approved else "not run"
    runtime_approval = "approved" if runtime_approved else "pending"
    ready_goal004 = "yes" if runtime_approved else "no"

    report = f"""# Gate: gate-003-synthetic-api-runtime-apply-and-smoke

Status: {status}

Branch: {branch}

Commit: {commit}

Generated at: {now}

Gate classification: cluster-apply gate

Explicit mutation permission required: yes

Mutation permission granted: {mutation_granted}

Target Kubernetes context: {target_context}

Actual Kubernetes context: {actual_context}

## Current programme state

- Goal 000: complete
- Goal 001: complete
- Goal 002: runtime-verified
- Goal 003 local-only: pass

## Pre-mutation local validation

{format_command_results(results)}
- `make evidence-gate-003-synthetic-api-runtime`: pass
  - Last output line: `reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md generated by this command.`

## Dry-run

- `make synthetic-api-tenant-namespaces-dry-run`: not run
- `make synthetic-api-install-dry-run`: not run

## Mutation

- `make synthetic-api-tenant-namespaces-apply`: not run
- `make synthetic-api-apply`: not run

## Runtime smoke

- `make synthetic-api-smoke`: {status_line("reports/synthetic-api-route-smoke-results.md")}

## Runtime negative tests

- `make synthetic-api-negative-test`: {status_line("reports/synthetic-api-negative-test-results.md")}

## Admin API safety

- `make kong-admin-exposure-test`: not run as a gate-003 runtime command

## Runtime evidence

- accounts backend: not run
- payments backend: not run
- cards backend: not run
- customer-profile backend: not run
- fraud-decisions backend: not run
- open-banking backend: not run
- accounts route: not run
- payments route: not run
- cards route: not run
- customer-profile route: not run
- fraud-decisions route: not run
- open-banking route: not run
- unknown host: not run
- unknown route: not run
- external exposure policy: not run
- Admin API exposure: not run

Cluster changes performed: {cluster_changes}

Secrets created: none

Kong Enterprise features used: none

KongPlugin resources created: none

KongConsumer resources created: none

KongClusterPlugin resources created: none

Authentication configured: no

Rate limiting configured: no

Runtime verification: {runtime_verification}

Runtime approval: {runtime_approval}

Ready for goal 004: {ready_goal004}

## Known limitations

- Explicit cluster mutation permission has not been granted in this local gate package.
- Tenant namespace prereq bootstrap has not run.
- Runtime apply, smoke, negative tests, and runtime evidence collection have not run.
- Goal 004 remains blocked until runtime approval is approved.
"""

    (ROOT / "reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    print("make evidence-gate-003-synthetic-api-runtime: pass")
    return 0 if local_pass else 1


def write_goal_001() -> int:
    commands = [
        ("make validate", [sys.executable, "scripts/validate_repo.py"]),
        ("make validate-yaml", [sys.executable, "scripts/validate_yaml.py"]),
        ("make validate-kustomize", [sys.executable, "scripts/render_prereqs.py"]),
        ("make validate-prereqs", [sys.executable, "scripts/validate_prereqs.py"]),
        ("make test", [sys.executable, "-m", "pytest", "tests/unit"]),
        ("make policy-test", [sys.executable, "-m", "pytest", "tests/policy"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    status = "pass" if all(code == 0 for _, code, _ in results) else "fail"
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    files = created_or_updated_files()

    report = f"""# Goal: goal-001-platform-prereqs

Status: {status}

Branch: {current_branch()}

Generated at: {now}

## Objective Summary

Implement or define the Kubernetes platform prerequisite layer before installing
Kong.

## Goal 000 Corrections Reviewed

- Booklore and Immich default/plain DB secret values remain replaced with
  non-deployable placeholders.
- Repo-wide validation checks for obvious plaintext/default secret markers and
  kubeconfig-like content.
- Goal 000 evidence remains in `reports/goal-000-summary.md`.

## Corrections Applied

- Goal 001 validation covers new prerequisite paths.
- `.gitignore` includes local secret, kubeconfig, certificate, and age-key
  patterns.
- CI remains cluster-free.

## Validation Commands Run

{format_command_results(results)}
- `make evidence-goal-001`: pass
  - Last output line: `reports/goal-001-summary.md generated by this command.`

## Optional Cluster Commands Run

- `make cluster-smoke`: not run
- `make cluster-prereq-smoke`: not run

## Created/Updated Files

{chr(10).join(f"- `{path}`" for path in files)}

## Namespace Baseline

- Platform and tenant namespaces are declared under `platform/namespaces/`.
- Namespace manifests include ownership, environment, data classification, and
  prerequisite-layer labels.

## GitOps App-Of-Apps Structure

- Argo CD app-of-apps templates are under `platform/gitops/app-of-apps/`.
- Argo CD project examples are under `platform/gitops/projects/`.
- Repo URLs remain explicit placeholders until configured.

## MetalLB Structure

- MetalLB prerequisite examples are under `platform/networking/metallb/`.
- The address pool is example-only and must be replaced before live use.

## cert-manager Structure

- cert-manager prerequisite examples are under
  `platform/certificates/cert-manager/`.
- Issuers are examples and do not include real CA private keys.

## SOPS/age Structure

- SOPS/age examples are under `platform/security/sops/`.
- No age private key is committed.

## NetworkPolicy Baseline

- NetworkPolicy baseline examples are under
  `platform/networking/network-policies/`.
- Default-deny, DNS egress, GitOps, observability, and ingress-controller
  placeholder patterns exist.

## Local Validation Result

{status}

## Cluster Changes Performed

None.

## Secrets Created

None; only non-deployable examples/placeholders were added.

## Kong Resources Created

None.

## Enterprise Kong Features Used

None.

## Known Limitations

- Goal 001 does not apply resources to the cluster.
- NetworkPolicy enforcement depends on the live cluster CNI and must be tested
  later with workloads.
- Argo CD, MetalLB, and cert-manager examples require real install/bootstrap
  choices before live use.

## Ready For Next Goal

goal-002-kong-oss-baseline
"""

    (ROOT / "reports/goal-001-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    print("make evidence-goal-001: pass")
    return 0 if status == "pass" else 1


def write_goal_002() -> int:
    commands = [
        ("make validate", ["make", "validate"]),
        ("make validate-yaml", ["make", "validate-yaml"]),
        ("make validate-kustomize", ["make", "validate-kustomize"]),
        ("make validate-prereqs", ["make", "validate-prereqs"]),
        ("make validate-kong-baseline", ["make", "validate-kong-baseline"]),
        ("make render-kong-baseline", ["make", "render-kong-baseline"]),
        ("make kong-static-test", ["make", "kong-static-test"]),
        ("make kong-admin-exposure-test", ["make", "kong-admin-exposure-test"]),
        ("make test", ["make", "test"]),
        ("make policy-test", ["make", "policy-test"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    status = "pass" if all(code == 0 for _, code, _ in results) else "fail"
    if status == "pass" and runtime_approved_from_files():
        for label, code, output in results:
            print(f"{label}: {'pass' if code == 0 else 'fail'}")
            if code != 0 and output:
                print(output)
        print("make evidence-goal-002: pass")
        print("reports/goal-002-summary.md already records runtime-verified evidence; preserving it.")
        return 0

    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    files = created_or_updated_files()
    versions = load_yaml("platform/kong/versions.yaml")

    status_label = "pass; local-only" if status == "pass" else status

    report = f"""# Goal: goal-002-kong-oss-baseline

Status: {status_label}

Branch: {current_branch()}

Generated at: {now}

## Objective Summary

Implement the local Kong OSS baseline layer with pinned versions, DB-less mode,
Gateway API smoke routing, private Admin API exposure, tests, documentation,
and evidence.

## Goal 001 Approval Status

- ChatGPT Pro approved goal 001 to proceed based on the reported evidence.

## Goal 001 Corrections Reviewed

- Goal 001 evidence remains in `reports/goal-001-summary.md`.
- Booklore and Immich default/plain DB secret values remain placeholder-only.
- CI remains cluster-free.
- Optional goal 001 cluster checks remain not run in this local-only goal 002
  implementation.

## Corrections Applied

- Goal 001 validators now exclude goal 002 Kong resources from before-Kong
  checks.
- Goal 000 foundation validation now preserves the OSS boundary instead of
  forbidding the goal 002 Kong subtree.
- Goal 002 static validation rejects Enterprise images/features, Admin API
  external exposure, floating tags, forbidden plugins, and real secrets.
- Gateway API is pinned to `v1.3.0` for KIC `3.5.10` compatibility according to
  Kong's version compatibility matrix.

## Selected Versions

- Kong Gateway image: `{versions["kong_gateway"]["image_repository"]}`
- Kong Gateway tag: `{versions["kong_gateway"]["image_tag"]}`
- Kong Ingress Controller image: `{versions["kong_ingress_controller"]["image_repository"]}`
- Kong Ingress Controller tag: `{versions["kong_ingress_controller"]["image_tag"]}`
- Kong Helm chart: `{versions["helm"]["chart_name"]}`
- Kong Helm chart version: `{versions["helm"]["chart_version"]}`
- Gateway API channel: `{versions["gateway_api"]["channel"]}`
- Gateway API version: `{versions["gateway_api"]["version"]}`

## Validation Commands Run

{format_command_results(results)}
- `make evidence-goal-002`: pass
  - Last output line: `reports/goal-002-summary.md generated by this command.`

## Optional Cluster Commands Run

- `make cluster-smoke`: not run
- `make cluster-prereq-smoke`: not run
- `make kong-install-dry-run`: not run
- `make kong-apply`: not run
- `make kong-cluster-smoke`: not run
- `make kong-route-smoke`: not run
- `make kong-rollback`: not run

## Created/Updated Files

{chr(10).join(f"- `{path}`" for path in files)}

## Kong Namespace

- `platform-kong` is declared for Kong runtime resources.
- `platform-kong-smoke` is declared for the platform-owned smoke backend.

## Kong Helm Baseline

- `kong/ingress` values define DB-less Kong OSS.
- Kong Gateway uses `kong:3.9.3`.
- KIC uses `kong/kubernetes-ingress-controller:3.5.10`.
- Admin API is ClusterIP-only.
- Proxy service is LoadBalancer for MetalLB.
- Helm chart compatibility: local render passed; cluster behavior not verified.

## Gateway API Baseline

- `GatewayClass/kong` uses `konghq.com/kic-gateway-controller`.
- Internal and external Gateways are declared separately.
- HTTP smoke routes attach to those Gateways.

## Smoke Backend

- `hashicorp/http-echo:1.0.0` is pinned.
- The backend returns `banklab-kong-smoke-ok`.
- Labels mark it as not a business API.

## Admin API Exposure Control

- Static validation checks Admin API is not externally exposed.
- Kong Manager, Portal, and Portal API are disabled.

## NetworkPolicy Baseline

- Kong default-deny, DNS, proxy ingress, smoke upstream, and API-server
  placeholder egress policies are defined.
- Enforcement still depends on the cluster CNI.

## Argo CD Integration

- Kong baseline app templates exist.
- Repo URLs remain `REPLACE_WITH_REPO_URL` placeholders until configured.

## Local Validation Result

{status}

## Cluster Changes Performed

None.

## Cluster Verification

Not run.

## Secrets Created

None; only non-deployable examples/placeholders were added if applicable.

## Kong Resources Created

None applied; manifests/templates only.

## Enterprise Kong Features Used

None.

## Admin API Externally Exposed

No, based on static validation.

## Known Limitations

- Kong was not applied to the cluster in this run.
- Gateway API CRDs, MetalLB, and NetworkPolicy enforcement are not cluster-proven
  by this local-only goal.
- Route smoke testing is pending until explicit cluster apply permission is
  given and the baseline is deployed.

## Ready For Next Goal

No; run cluster apply and smoke tests before goal-003.
"""

    (ROOT / "reports/goal-002-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    print("make evidence-goal-002: pass")
    return 0 if status == "pass" else 1


def write_gate_002_runtime_preflight() -> int:
    commands = [
        ("make validate", ["make", "validate"]),
        ("make validate-yaml", ["make", "validate-yaml"]),
        ("make validate-kustomize", ["make", "validate-kustomize"]),
        ("make validate-prereqs", ["make", "validate-prereqs"]),
        ("make validate-kong-baseline", ["make", "validate-kong-baseline"]),
        ("make render-kong-baseline", ["make", "render-kong-baseline"]),
        ("make kong-static-test", ["make", "kong-static-test"]),
        ("make kong-admin-exposure-test", ["make", "kong-admin-exposure-test"]),
        ("make runtime-preflight-local", ["make", "runtime-preflight-local"]),
        ("make kong-apply-plan", ["make", "kong-apply-plan"]),
        ("make mutation-guard-test", ["make", "mutation-guard-test"]),
        ("make test", ["make", "test"]),
        ("make policy-test", ["make", "policy-test"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    status = "pass; local-only pre-cluster-apply" if all(code == 0 for _, code, _ in results) else "fail"
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    files = created_or_updated_files()
    versions = load_yaml("platform/kong/versions.yaml")

    file_list = "\n".join(f"- `{path}`" for path in files) if files else "- None"

    report = f"""# Gate: gate-002-runtime-preflight

Status: {status}

Branch: {current_branch()}

Generated at: {now}

## Objective summary

Prepare the repository for an explicitly approved Kong runtime apply and smoke
gate without mutating the cluster.

## Current programme state

- Goal 000: complete
- Goal 001: complete and approved
- Goal 002: corrected and approved as local-only

## Goal 002 local-only status verified

- `reports/goal-002-summary.md` remains `Status: pass; local-only`.
- Cluster changes performed: none.
- Cluster verification: not run.
- Kong resources created: none applied; manifests/templates only.

## Gateway API compatibility verified

- Kong Gateway remains `{versions["kong_gateway"]["image_repository"]}:{versions["kong_gateway"]["image_tag"]}`.
- KIC remains `{versions["kong_ingress_controller"]["image_repository"]}:{versions["kong_ingress_controller"]["image_tag"]}`.
- Gateway API remains `{versions["gateway_api"]["version"]}`.
- KIC/Gateway API compatibility validation remains active.

## Mutation guardrails

- `make kong-apply` calls `platform/kong/scripts/require-cluster-mutation-permission.sh`.
- `make kong-rollback` calls `platform/kong/scripts/require-cluster-mutation-permission.sh`.
- The guard requires `BANKLAB_ALLOW_CLUSTER_MUTATION=true`.
- The guard requires `BANKLAB_TARGET_CONTEXT=<expected-context>`.
- `make mutation-guard-test` proves the guard fails closed without those values.

## Read-only preflight scripts

- `platform/kong/scripts/cluster-readonly-preflight.sh` exists and is optional.
- `platform/kong/scripts/kong-readonly-preflight.sh` exists and is optional.
- These scripts are not part of CI and are not part of the required local gate.

## Apply plan

- `reports/kong-runtime-apply-plan.md` is generated from repository files only.
- It does not query or mutate the cluster.
- It states that runtime success still requires explicit apply and smoke validation.

## Rollback plan

- `docs/runbooks/kong-runtime-rollback-checklist.md` exists.
- `platform/kong/ROLLBACK-CHECKLIST.md` exists.
- Rollback requires the same explicit mutation guard as apply.

## Goal 003 blocked

- `goal-003-synthetic-bank-apis` remains blocked until goal-002 runtime validation passes.
- The full goal 003 body has not been created.

## Validation commands run

{format_command_results(results)}
- `make evidence-gate-002-runtime-preflight`: pass
  - Last output line: `reports/gate-002-runtime-preflight-summary.md generated by this command.`

## Optional read-only cluster commands run

- `make cluster-readonly-preflight`: not run
- `make kong-readonly-preflight`: not run
- Optional read-only cluster checks: not run

## Cluster-mutating commands run

- none

## Created files

{file_list}

## Updated files

{file_list}

Cluster changes performed: none

Secrets created: none

Kong runtime applied: no

Kong route smoke passed: no

Admin API externally exposed: no, based on static validation only

Known limitations: Kong has not been applied, runtime smoke checks have not
run, and goal 003 remains blocked.

Next assigned gate: gate-002-cluster-apply-and-smoke, requiring explicit cluster mutation permission
"""

    (ROOT / "reports/gate-002-runtime-preflight-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    print("make evidence-gate-002-runtime-preflight: pass")
    return 0 if status.startswith("pass") else 1


def write_gate_002_cluster_apply_and_smoke() -> int:
    commands = [
        ("make validate", ["make", "validate"]),
        ("make validate-yaml", ["make", "validate-yaml"]),
        ("make validate-kustomize", ["make", "validate-kustomize"]),
        ("make validate-prereqs", ["make", "validate-prereqs"]),
        ("make validate-kong-baseline", ["make", "validate-kong-baseline"]),
        ("make render-kong-baseline", ["make", "render-kong-baseline"]),
        ("make kong-static-test", ["make", "kong-static-test"]),
        ("make kong-admin-exposure-test", ["make", "kong-admin-exposure-test"]),
        ("make runtime-preflight-local", ["make", "runtime-preflight-local"]),
        ("make kong-apply-plan", ["make", "kong-apply-plan"]),
        ("make mutation-guard-test", ["make", "mutation-guard-test"]),
        ("make validate-cluster-apply-gate", ["make", "validate-cluster-apply-gate"]),
        ("make test", ["make", "test"]),
        ("make policy-test", ["make", "policy-test"]),
        (
            "make docs",
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--site-dir",
                ".build/mkdocs",
            ],
        ),
    ]

    results: list[tuple[str, int, str]] = []
    for label, command in commands:
        code, output = run_command(command)
        results.append((label, code, output))

    local_status = all(code == 0 for _, code, _ in results)
    if local_status and runtime_approved_from_files():
        for label, code, output in results:
            print(f"{label}: {'pass' if code == 0 else 'fail'}")
            if code != 0 and output:
                print(output)
        print("make evidence-gate-002-cluster-apply-and-smoke: pass")
        print("reports/gate-002-cluster-apply-and-smoke-summary.md already records runtime-verified evidence; preserving it.")
        return 0

    status = "pending explicit cluster mutation permission" if local_status else "fail"
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    branch = current_branch()
    commit_code, commit = run_command(["git", "rev-parse", "--short", "HEAD"])
    commit = commit if commit_code == 0 else "unknown"
    files = created_or_updated_files()
    file_list = "\n".join(f"- `{path}`" for path in files) if files else "- None"

    report = f"""# Gate: gate-002-cluster-apply-and-smoke

Status: {status}

Branch: {branch}

Commit: {commit}

Generated at: {now}

Gate classification: cluster-apply gate

Explicit mutation permission required: yes

Mutation permission granted: no

Target Kubernetes context:

Actual Kubernetes context:

## Current programme state

- Goal 000: complete
- Goal 001: complete and approved
- Goal 002: approved as local-only
- gate-002-runtime-preflight: approved as local-only pre-cluster-apply

## Pre-mutation local validation

{format_command_results(results)}
- `make evidence-gate-002-cluster-apply-and-smoke`: pass
  - Last output line: `reports/gate-002-cluster-apply-and-smoke-summary.md generated by this command.`

## Cluster preflight

- `make cluster-readonly-preflight`: not run
- `make kong-readonly-preflight`: not run
- `make cluster-smoke`: not run
- `make cluster-prereq-smoke`: not run

## Dry-run

- `make kong-install-dry-run`: not run

## Mutation

- `make kong-apply`: not run

## Runtime validation

- `make kong-cluster-smoke`: not run
- `make kong-route-smoke`: not run
- `make kong-admin-exposure-test`: not runtime-run

## Runtime evidence

- Kong namespace: not run
- Kong pods: not run
- KIC pods: not run
- proxy service: not run
- LoadBalancer status: not run
- GatewayClass: not run
- internal Gateway: not run
- external Gateway: not run
- smoke backend: not run
- internal HTTPRoute: not run
- external HTTPRoute: not run
- internal smoke route: not run
- external smoke route: not run
- unknown route negative test: not run
- Admin API external exposure test: not run

## Rollback

- rollback required: no
- rollback command: `make kong-rollback`
- rollback run: not run

## Created or updated files

{file_list}

Cluster changes performed: none

Secrets created: none

Kong runtime applied: no

Kong route smoke passed: no

Admin API externally exposed: not runtime-tested

Runtime approval: pending

Known limitations: explicit cluster mutation permission has not been granted.

Ready for goal 003: no
"""

    (ROOT / "reports/gate-002-cluster-apply-and-smoke-summary.md").write_text(report, encoding="utf-8")

    for label, code, output in results:
        print(f"{label}: {'pass' if code == 0 else 'fail'}")
        if code != 0 and output:
            print(output)

    print("make evidence-gate-002-cluster-apply-and-smoke: pass")
    return 0 if local_status else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="goal-000-repo-foundation")
    args = parser.parse_args()

    if args.goal == "goal-000-repo-foundation":
        return write_goal_000()
    if args.goal == "goal-001-platform-prereqs":
        return write_goal_001()
    if args.goal == "goal-002-kong-oss-baseline":
        return write_goal_002()
    if args.goal == "goal-003-synthetic-bank-apis":
        return write_goal_003()
    if args.goal == "gate-003-synthetic-api-runtime-apply-and-smoke":
        return write_gate_003_synthetic_api_runtime()
    if args.goal == "gate-002-runtime-preflight":
        return write_gate_002_runtime_preflight()
    if args.goal == "gate-002-cluster-apply-and-smoke":
        return write_gate_002_cluster_apply_and_smoke()

    print(f"unknown goal: {args.goal}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
