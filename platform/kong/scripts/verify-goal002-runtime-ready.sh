#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${repo_root}"

failures=()

require_contains() {
  local file="$1"
  local expected="$2"
  if [[ ! -f "${file}" ]]; then
    failures+=("missing ${file}")
    return
  fi
  if ! grep -Fqi "${expected}" "${file}"; then
    failures+=("${file} missing ${expected}")
  fi
}

for file in \
  platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md \
  platform/kong/CLUSTER-SMOKE-RESULTS.md \
  platform/kong/ROUTE-SMOKE-RESULTS.md \
  platform/kong/ADMIN-API-EXPOSURE-RESULTS.md; do
  require_contains "${file}" "Status: pass"
done

require_contains docs/decisions/goal-002-runtime-approval.md "Status: approved"
require_contains reports/gate-002-cluster-apply-and-smoke-summary.md "Status: pass; runtime-verified"
require_contains reports/gate-002-cluster-apply-and-smoke-summary.md "Kong runtime applied: yes"
require_contains reports/gate-002-cluster-apply-and-smoke-summary.md "Kong route smoke passed: yes"
require_contains reports/gate-002-cluster-apply-and-smoke-summary.md "Admin API externally exposed: no"
require_contains reports/gate-002-cluster-apply-and-smoke-summary.md "Runtime approval: approved"
require_contains reports/gate-002-cluster-apply-and-smoke-summary.md "Ready for goal 003: yes"
require_contains reports/goal-002-summary.md "runtime-verified"

if ((${#failures[@]} > 0)); then
  echo "Goal 002 runtime readiness is not approved:"
  for failure in "${failures[@]}"; do
    echo "- ${failure}"
  done
  exit 1
fi

echo "Goal 002 runtime readiness is approved."
