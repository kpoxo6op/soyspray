#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
log="${repo_root}/platform/kong/security-controls/RUNTIME-APPLY-EXECUTION-LOG.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh

status="pass"
if ! scripts/render_goal004_security_controls.py | kubectl apply -f - >"${tmp_output}" 2>&1; then
  status="fail"
fi

{
  echo "# Goal004 Security Runtime Apply Execution Log"
  echo
  echo "Status: ${status}"
  echo
  echo "Supported states: not run, pass, fail, blocked, partial"
  echo
  echo "Command: make goal004-security-apply"
  echo
  echo "Timestamp: $(date -Iseconds)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "## Output"
  cat "${tmp_output}"
} >"${log}"

cat "${tmp_output}"
if [[ "${status}" != "pass" ]]; then
  exit 1
fi
