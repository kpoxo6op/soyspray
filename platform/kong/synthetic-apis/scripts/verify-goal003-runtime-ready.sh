#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

require_marker() {
  local file="$1"
  local marker="$2"
  if ! grep -Fq "${marker}" "${repo_root}/${file}"; then
    echo "Missing goal003 runtime-ready marker in ${file}: ${marker}" >&2
    return 1
  fi
}

reject_marker() {
  local file="$1"
  local marker="$2"
  if grep -Fq "${marker}" "${repo_root}/${file}"; then
    echo "Runtime-ready is blocked by marker in ${file}: ${marker}" >&2
    return 1
  fi
}

require_marker reports/goal-003-summary.md "Status: pass; runtime-verified"
require_marker reports/goal-003-summary.md "Cluster changes performed: synthetic bank APIs applied"
require_marker reports/goal-003-summary.md "Runtime verification: pass"
require_marker reports/goal-003-summary.md "Ready for next goal: goal-004-auth-rate-limit-security"
require_marker reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md "Status: pass; runtime-verified"
require_marker reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md "Runtime approval: approved"
require_marker reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md "Ready for goal 004: yes"
require_marker docs/decisions/goal-003-runtime-approval.md "Status: approved"

for file in \
  platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md \
  platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md \
  platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md \
  platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md \
  reports/synthetic-api-runtime-evidence.md \
  reports/synthetic-api-route-smoke-results.md \
  reports/synthetic-api-negative-test-results.md; do
  require_marker "${file}" "Status: pass"
  reject_marker "${file}" "Status: not run"
  reject_marker "${file}" "Status: fail"
  reject_marker "${file}" "Status: blocked"
  reject_marker "${file}" "Status: partial"
done

echo "Goal 003 runtime readiness is approved."
