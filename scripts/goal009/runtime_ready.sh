#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
report="${repo_root}/reports/goal-009-runtime-readiness.md"
tmp_output="$(mktemp)"
tmp_dryrun="$(mktemp)"
trap 'rm -f "${tmp_output}" "${tmp_dryrun}"' EXIT
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
    echo "# Goal009 Runtime Readiness"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Readiness command: make goal009-runtime-ready"
    echo
    echo "Mutation behavior: no Goal009 plugin apply is performed by this command."
    echo
    echo "## Server dry-run output"
    cat "${tmp_dryrun}"
    echo
    echo "## Readiness checks"
    cat "${tmp_output}"
  } >"${report}"
}

fail() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_report "fail"
  exit 1
}

blocked() {
  echo "$1" | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
}

cd "${repo_root}"
platform/kong/scripts/require-cluster-mutation-permission.sh

if "${python_bin}" scripts/render_goal009_response_headers.py | kubectl apply --dry-run=server -f - >"${tmp_dryrun}" 2>&1; then
  echo "goal009 render accepted by server dry-run: pass" | tee -a "${tmp_output}"
else
  cat "${tmp_dryrun}" >&2
  fail "goal009 server dry-run failed"
fi

kubectl -n tenant-accounts get httproute banklab-accounts >/dev/null || blocked "HTTPRoute tenant-accounts/banklab-accounts is not readable."
echo "accounts HTTPRoute readable: pass" | tee -a "${tmp_output}"

kubectl -n tenant-accounts get service banklab-accounts-api >/dev/null || blocked "Service tenant-accounts/banklab-accounts-api is not readable."
echo "accounts Service readable: pass" | tee -a "${tmp_output}"

kubectl -n synthetic-clients get secret banklab-mobile-banking-app-key-auth >/dev/null || blocked "Mobile banking key-auth Secret is not readable."
kubectl -n synthetic-clients get secret banklab-internet-banking-web-key-auth >/dev/null || blocked "Internet banking key-auth Secret is not readable."
echo "runtime credential Secrets readable: pass" | tee -a "${tmp_output}"

if ! proxy_ip="$(kubectl -n platform-kong get service banklab-kong-gateway-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" || [[ -z "${proxy_ip}" ]]; then
  blocked "Kong proxy LoadBalancer IP not available."
fi
echo "Kong proxy IP available: pass; ip=${proxy_ip}" | tee -a "${tmp_output}"

plugins="$(kubectl -n tenant-accounts get httproute banklab-accounts -o jsonpath='{.metadata.annotations.konghq\.com/plugins}' 2>/dev/null || true)"
if [[ "${plugins}" == *"banklab-goal009-security-headers"* ]]; then
  fail "Goal009 plugin is already attached before rollout."
fi
echo "Goal009 plugin not attached before rollout: pass" | tee -a "${tmp_output}"

write_report "pass"
echo "${report#${repo_root}/} generated."
