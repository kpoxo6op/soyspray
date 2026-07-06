#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

require_marker() {
  local file="$1"
  local marker="$2"
  if ! grep -Fq "${marker}" "${repo_root}/${file}"; then
    echo "Missing runtime-ready marker in ${file}: ${marker}" >&2
    return 1
  fi
}

require_marker reports/goal-003-summary.md "Status: pass; runtime-verified"
require_marker reports/goal-003-summary.md "Runtime verification: pass"
require_marker reports/goal-003-summary.md "Ready for next goal: goal-004-auth-rate-limit-security"
require_marker reports/synthetic-api-runtime-evidence.md "Status: pass"
require_marker reports/synthetic-api-route-smoke-results.md "Status: pass"
require_marker reports/synthetic-api-negative-test-results.md "Status: pass"

echo "Synthetic API runtime readiness is approved."
