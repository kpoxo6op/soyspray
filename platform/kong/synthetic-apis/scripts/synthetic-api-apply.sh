#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
log="${repo_root}/platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT

"${repo_root}/platform/kong/scripts/require-cluster-mutation-permission.sh"
python_bin="${PYTHON:-${repo_root}/soyspray-venv/bin/python}"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="python3"
fi

status="pass"
if ! {
  "${python_bin}" "${repo_root}/scripts/render_synthetic_apis.py" --include-kind Namespace | kubectl apply -f -
  "${python_bin}" "${repo_root}/scripts/render_synthetic_apis.py" --exclude-kind Namespace | kubectl apply -f -
} >"${tmp_output}" 2>&1; then
  status="fail"
fi

{
  echo "# Synthetic API Runtime Apply Execution Log"
  echo
  echo "Status: ${status}"
  echo
  echo "Supported states: not run, pass, fail, blocked, partial"
  echo
  echo "Command: make synthetic-api-apply"
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
