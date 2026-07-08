#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/goal004-runtime-credentials-results.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT

write_report() {
  local status="$1"
  {
    echo "# Goal004 Runtime Credentials"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Credential source: local environment variables"
    echo
    echo "Secret values are not printed or committed."
    echo
    echo "## Applied objects"
    cat "${tmp_output}"
  } >"${report}"
}

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh

if scripts/render_goal004_runtime_credentials.py | kubectl apply -f - | tee "${tmp_output}"; then
  write_report "pass"
else
  write_report "fail"
  exit 1
fi

echo "${report#${repo_root}/} generated."
