#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-005-tenancy-rbac-apply.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT
python_bin="${BANKLAB_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh

status="pass"
if ! "${python_bin}" scripts/render_goal005_tenancy_rbac.py | kubectl apply -f - >"${tmp_output}" 2>&1; then
  status="fail"
fi

{
  echo "# Goal005 Tenancy RBAC Apply"
  echo
  echo "Status: ${status}"
  echo
  echo "Supported states: not run, pass, fail, blocked, partial"
  echo
  echo "Command: make goal005-tenancy-rbac-apply"
  echo
  echo "Generated at: $(date -Iseconds)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "## Output"
  cat "${tmp_output}"
} >"${report}"

cat "${tmp_output}"
if [[ "${status}" != "pass" ]]; then
  exit 1
fi
echo "${report#${repo_root}/} generated."
