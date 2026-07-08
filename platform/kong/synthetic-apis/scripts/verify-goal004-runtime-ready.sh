#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

require_marker() {
  local file="$1"
  local marker="$2"
  if ! grep -Fq "${marker}" "${repo_root}/${file}"; then
    echo "Missing goal004 runtime-ready marker in ${file}: ${marker}" >&2
    return 1
  fi
}

reject_marker() {
  local file="$1"
  local marker="$2"
  if grep -Fq "${marker}" "${repo_root}/${file}"; then
    echo "Goal004 runtime-ready is blocked by marker in ${file}: ${marker}" >&2
    return 1
  fi
}

require_marker reports/goal-004-summary.md "Status: pass; runtime-verified"
require_marker reports/goal-004-summary.md "Authentication configured: key-auth and jwt"
require_marker reports/goal-004-summary.md "Authorization configured: acl"
require_marker reports/goal-004-summary.md "Rate limiting configured: rate-limiting"
require_marker reports/goal-004-summary.md "Ready for next goal: goal-005-tenancy-rbac-change-control"
require_marker docs/decisions/goal-004-runtime-approval.md "Status: approved"

for file in \
  reports/goal004-runtime-credentials-results.md \
  reports/goal004-security-runtime-state.md \
  reports/goal004-security-smoke-results.md \
  reports/goal004-security-negative-test-results.md \
  reports/goal004-rate-limit-results.md \
  platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md \
  platform/kong/security-controls/RUNTIME-APPLY-EXECUTION-LOG.md \
  platform/kong/security-controls/RUNTIME-SMOKE-RESULTS.md \
  platform/kong/security-controls/RUNTIME-NEGATIVE-TEST-RESULTS.md \
  platform/kong/security-controls/RUNTIME-RATE-LIMIT-RESULTS.md \
  platform/kong/security-controls/RUNTIME-ADMIN-API-SAFETY-RESULTS.md; do
  require_marker "${file}" "Status: pass"
  reject_marker "${file}" "Status: not run"
  reject_marker "${file}" "Status: fail"
  reject_marker "${file}" "Status: blocked"
  reject_marker "${file}" "Status: partial"
done

echo "Goal 004 runtime readiness is approved."
