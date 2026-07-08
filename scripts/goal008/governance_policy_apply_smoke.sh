#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-008-governance-policy-rollout.md"
tmp_output="$(mktemp)"
tmp_apply="$(mktemp)"
tmp_safe="$(mktemp)"
tmp_unsafe="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_apply}" "${tmp_safe}" "${tmp_unsafe}"' EXIT
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
    echo "# Goal008 Governance Policy Rollout Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Policy: banklab-kong-plugin-governance"
    echo
    echo "Runtime kind: ValidatingAdmissionPolicy"
    echo
    echo "Validation action: Deny"
    echo
    echo "## Apply output"
    cat "${tmp_apply}"
    echo
    echo "## Safe fixture server dry-run"
    cat "${tmp_safe}"
    echo
    echo "## Unsafe fixture server dry-run"
    cat "${tmp_unsafe}"
    echo
    echo "## Runtime smoke"
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

"${python_bin}" scripts/render_goal008_governance_policy.py | kubectl apply -f - >"${tmp_apply}" 2>&1 || {
  cat "${tmp_apply}" >&2
  write_report "fail"
  exit 1
}

kubectl get validatingadmissionpolicy banklab-kong-plugin-governance >/dev/null || fail "ValidatingAdmissionPolicy missing after apply"
kubectl get validatingadmissionpolicybinding banklab-kong-plugin-governance >/dev/null || fail "ValidatingAdmissionPolicyBinding missing after apply"
echo "admission policy and binding applied: pass" | tee -a "${tmp_output}"

if "${python_bin}" scripts/render_goal008_governance_policy.py --safe-fixture | kubectl apply --dry-run=server -f - >"${tmp_safe}" 2>&1; then
  echo "safe KongPlugin fixture accepted by server dry-run: pass" | tee -a "${tmp_output}"
else
  cat "${tmp_safe}" >&2
  fail "safe KongPlugin fixture was rejected"
fi

if "${python_bin}" scripts/render_goal008_governance_policy.py --unsafe-fixture | kubectl apply --dry-run=server -f - >"${tmp_unsafe}" 2>&1; then
  cat "${tmp_unsafe}" >&2
  fail "unsafe KongPlugin fixture was unexpectedly accepted"
else
  if grep -Fq "banklab Kong governance allowlist" "${tmp_unsafe}"; then
    echo "unsafe KongPlugin fixture rejected by governance policy: pass" | tee -a "${tmp_output}"
  else
    cat "${tmp_unsafe}" >&2
    fail "unsafe KongPlugin fixture failed, but not with the governance allowlist message"
  fi
fi

write_report "pass"
echo "${report#${repo_root}/} generated."
