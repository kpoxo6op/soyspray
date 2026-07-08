#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
decision="${repo_root}/docs/decisions/goal-005-runtime-approval.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT

cd "${repo_root}"

run_step() {
  local label="$1"
  shift
  echo "## ${label}" >>"${tmp_output}"
  "$@" >>"${tmp_output}" 2>&1
  echo >>"${tmp_output}"
}

run_step "goal005 tenancy/RBAC apply" make goal005-tenancy-rbac-apply
run_step "goal005 RBAC smoke" make goal005-rbac-smoke
sleep 2
run_step "goal005 sample change apply and smoke" make goal005-change-apply-and-smoke
sleep 2
run_step "goal005 sample change rollback and smoke" make goal005-change-rollback-and-smoke
sleep 2
run_step "goal004 positive smoke after rollback" make goal004-security-smoke
run_step "goal004 negative auth behavior after rollback" make goal004-security-negative-test
run_step "goal004 Redis rate-limit behavior after rollback" make goal004-rate-limit-test
run_step "Kong Admin API exposure safety" make kong-admin-exposure-test

{
  echo "# Goal005 Runtime Approval"
  echo
  echo "Status: pending approval"
  echo
  echo "Generated at: $(date -Iseconds)"
  echo
  echo "Branch: $(git branch --show-current)"
  echo
  echo "Commit: $(git rev-parse --short HEAD)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "## Summary"
  echo
  echo "Goal005 runtime acceptance passed locally and is ready for ChatGPT Pro review."
  echo
  echo "## Evidence links"
  echo
  echo "- reports/goal-005-rbac-runtime.md"
  echo "- reports/goal-005-change-rollout.md"
  echo "- reports/goal-005-change-rollback.md"
  echo "- reports/goal004-security-smoke-results.md"
  echo "- reports/goal004-security-negative-test-results.md"
  echo "- reports/goal004-rate-limit-results.md"
  echo
  echo "## Known issues"
  echo
  echo "- None from the runtime acceptance sequence."
  echo
  echo "## Rollback notes"
  echo
  echo "- Sample change rollback removes only the goal005 response header plugin and reapplies the stable route annotation set."
  echo "- Stable tenancy/RBAC resources remain applied."
  echo
  echo "## Ready-for-approval statement"
  echo
  echo "Goal005 is ready for Pro approval after evidence is committed and pushed."
} >"${decision}"

cat "${tmp_output}"
echo "${decision#${repo_root}/} generated."
