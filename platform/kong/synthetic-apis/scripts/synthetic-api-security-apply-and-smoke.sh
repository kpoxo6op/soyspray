#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${repo_root}"

echo "Branch: $(git branch --show-current 2>/dev/null || true)"
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || true)"
echo "Current Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"

platform/kong/scripts/require-cluster-mutation-permission.sh

make goal003-runtime-ready
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make validate-goal004-security
make openapi-lint
make render-synthetic-apis
make render-goal004-security
make goal004-static-test
make goal004-contract-test
make goal004-smoke-plan
make test
make policy-test
make docs
make evidence-goal-004

make goal004-runtime-credentials-dry-run
make goal004-security-dry-run
make goal004-runtime-credentials-apply
make goal004-security-apply
make goal004-security-smoke
make goal004-security-negative-test
make goal004-rate-limit-test
if make kong-admin-exposure-test; then
  {
    echo "# Goal004 Runtime Admin API Safety Results"
    echo
    echo "Status: pass"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Command: make kong-admin-exposure-test"
    echo
    echo "Timestamp: $(date -Iseconds)"
    echo
    echo "Result summary: Admin API external exposure check passed."
  } > platform/kong/security-controls/RUNTIME-ADMIN-API-SAFETY-RESULTS.md
else
  {
    echo "# Goal004 Runtime Admin API Safety Results"
    echo
    echo "Status: fail"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Command: make kong-admin-exposure-test"
    echo
    echo "Timestamp: $(date -Iseconds)"
    echo
    echo "Result summary: Admin API external exposure check failed."
  } > platform/kong/security-controls/RUNTIME-ADMIN-API-SAFETY-RESULTS.md
  exit 1
fi

platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-security-evidence.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh

{
  echo "# Goal 004 Runtime Approval"
  echo
  echo "Status: approved"
  echo
  echo "Approved at: $(date -Iseconds)"
  echo
  echo "Branch: $(git branch --show-current 2>/dev/null || true)"
  echo
  echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || true)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "Goal 004 runtime approval is granted after guarded runtime credentials,"
  echo "security-control apply, positive smoke, negative auth checks,"
  echo "Redis-backed rate-limit tests, Admin API safety checks, and evidence"
  echo "collection passed for the synthetic banking API layer."
  echo
  echo "- Cluster changes performed: goal004 security controls applied."
  echo "- Credential source: local environment variables; values not logged."
  echo "- Runtime verification: pass."
  echo "- Runtime approval: approved."
  echo "- Ready for goal 005: yes."
} > docs/decisions/goal-004-runtime-approval.md

make evidence-goal-004
make goal004-runtime-ready
