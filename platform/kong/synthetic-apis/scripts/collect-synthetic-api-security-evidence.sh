#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/goal004-security-runtime-state.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT

apis=(
  "accounts tenant-accounts banklab-accounts"
  "payments tenant-payments banklab-payments"
  "cards tenant-cards banklab-cards"
  "customer-profile tenant-customer-profile banklab-customer-profile"
  "fraud-decisions tenant-fraud banklab-fraud-decisions"
  "open-banking tenant-open-banking banklab-open-banking"
)

write_report() {
  local status="$1"
  {
    echo "# Goal004 Security Runtime State"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "Credential source: runtime-generated-not-committed"
    echo
    echo "## Checks"
    cat "${tmp_output}"
    echo
    echo "## KongPlugins"
    kubectl get kongplugin -A -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true || true
    echo
    echo "## KongConsumers"
    kubectl -n synthetic-clients get kongconsumer -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true || true
    echo
    echo "## Credential Secret Names"
    kubectl -n synthetic-clients get secret -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true || true
    echo
    echo "Secret values are intentionally not printed."
  } >"${report}"
}

if ! kubectl version --client >/dev/null 2>&1 || ! kubectl cluster-info >/dev/null 2>&1; then
  echo "kubectl cannot reach a Kubernetes API server." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

status="pass"
plugin_count="$(kubectl get kongplugin -A -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true --no-headers 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${plugin_count}" == "24" ]]; then
  echo "KongPlugin count: pass; count=24" | tee -a "${tmp_output}"
else
  echo "KongPlugin count: fail; expected 24; got ${plugin_count}" | tee -a "${tmp_output}" >&2
  status="fail"
fi

consumer_count="$(kubectl -n synthetic-clients get kongconsumer -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true --no-headers 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${consumer_count}" == "6" ]]; then
  echo "KongConsumer count: pass; count=6" | tee -a "${tmp_output}"
else
  echo "KongConsumer count: fail; expected 6; got ${consumer_count}" | tee -a "${tmp_output}" >&2
  status="fail"
fi

secret_count="$(kubectl -n synthetic-clients get secret -l banklab.konghq.com/goal=goal-004 --ignore-not-found=true --no-headers 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${secret_count}" == "12" ]]; then
  echo "credential Secret count: pass; count=12; values-not-printed" | tee -a "${tmp_output}"
else
  echo "credential Secret count: fail; expected 12; got ${secret_count}" | tee -a "${tmp_output}" >&2
  status="fail"
fi

for entry in "${apis[@]}"; do
  read -r api namespace route <<<"${entry}"
  plugins="$(kubectl -n "${namespace}" get "httproute/${route}" -o jsonpath='{.metadata.annotations.konghq\.com/plugins}' 2>/dev/null || true)"
  expected="banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id"
  if [[ "${api}" == "open-banking" ]]; then
    expected="banklab-jwt,banklab-acl,banklab-rate-limit,banklab-correlation-id"
  fi
  if [[ "${plugins}" == "${expected}" ]]; then
    echo "${api} route plugins: pass" | tee -a "${tmp_output}"
  else
    echo "${api} route plugins: fail; got ${plugins:-missing}" | tee -a "${tmp_output}" >&2
    status="fail"
  fi
done

write_report "${status}"
if [[ "${status}" != "pass" ]]; then
  exit 1
fi

echo "${report#${repo_root}/} generated."
