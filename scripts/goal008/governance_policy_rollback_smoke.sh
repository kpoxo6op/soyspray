#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-008-governance-policy-rollback.md"
tmp_output="$(mktemp)"
tmp_rollback="$(mktemp)"
tmp_unsafe="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_rollback}" "${tmp_unsafe}"' EXIT
python_bin="${BANKLAB_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
  if [[ -x "${repo_root}/soyspray-venv/bin/python" ]]; then
    python_bin="${repo_root}/soyspray-venv/bin/python"
  else
    python_bin="python3"
  fi
fi

write_report() {
  local status="$1"
  {
    echo "# Goal008 Governance Policy Rollback Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Rollback command: make goal008-governance-policy-rollback-and-smoke"
    echo
    echo "Resources removed: ValidatingAdmissionPolicyBinding/banklab-kong-plugin-governance and ValidatingAdmissionPolicy/banklab-kong-plugin-governance"
    echo
    echo "## Rollback output"
    cat "${tmp_rollback}"
    echo
    echo "## Unsafe fixture server dry-run after rollback"
    cat "${tmp_unsafe}"
    echo
    echo "## Runtime smoke after rollback"
    cat "${tmp_output}"
  } >"${report}"
}

fail() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_report "fail"
  exit 1
}

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh

"${python_bin}" scripts/render_goal008_governance_policy.py --delete | kubectl delete --ignore-not-found=true -f - >"${tmp_rollback}" 2>&1 || {
  cat "${tmp_rollback}" >&2
  write_report "fail"
  exit 1
}

if kubectl get validatingadmissionpolicybinding banklab-kong-plugin-governance >/dev/null 2>&1; then
  fail "ValidatingAdmissionPolicyBinding still exists after rollback"
fi
if kubectl get validatingadmissionpolicy banklab-kong-plugin-governance >/dev/null 2>&1; then
  fail "ValidatingAdmissionPolicy still exists after rollback"
fi
echo "admission policy and binding removed: pass" | tee -a "${tmp_output}"

if "${python_bin}" scripts/render_goal008_governance_policy.py --unsafe-fixture | kubectl apply --dry-run=server -f - >"${tmp_unsafe}" 2>&1; then
  echo "unsafe KongPlugin fixture dry-run is admissible after rollback: pass" | tee -a "${tmp_output}"
else
  cat "${tmp_unsafe}" >&2
  fail "unsafe KongPlugin fixture still rejected after rollback"
fi

write_report "pass"
echo "${report#${repo_root}/} generated."
