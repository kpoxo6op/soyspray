#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${repo_root}"

echo "Branch: $(git branch --show-current 2>/dev/null || true)"
echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || true)"
echo "Current Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"

platform/kong/scripts/require-cluster-mutation-permission.sh

make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
make test
make policy-test
make docs
make validate-synthetic-api-runtime-gate

make synthetic-api-install-dry-run
make synthetic-api-apply
make synthetic-api-smoke
make synthetic-api-negative-test
if make kong-admin-exposure-test; then
  {
    echo "# Synthetic API Runtime Admin API Safety Results"
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
  } > platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md
else
  {
    echo "# Synthetic API Runtime Admin API Safety Results"
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
  } > platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md
  exit 1
fi
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
make evidence-goal-003
make evidence-gate-003-synthetic-api-runtime
make goal003-runtime-ready
