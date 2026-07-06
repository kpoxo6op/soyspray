#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/synthetic-api-runtime-evidence.md"
tmp_output="$(mktemp)"
trap 'rm -f "${tmp_output}"' EXIT

apis=(
  "accounts tenant-accounts banklab-accounts-api banklab-accounts"
  "payments tenant-payments banklab-payments-api banklab-payments"
  "cards tenant-cards banklab-cards-api banklab-cards"
  "customer-profile tenant-customer-profile banklab-customer-profile-api banklab-customer-profile"
  "fraud-decisions tenant-fraud banklab-fraud-decisions-api banklab-fraud-decisions"
  "open-banking tenant-open-banking banklab-open-banking-api banklab-open-banking"
)

write_report() {
  local status="$1"
  {
    echo "# Synthetic API Runtime Evidence"
    echo
    echo "Status: ${status}"
    echo
    echo "Supported states: not run, pass, fail, blocked, partial"
    echo
    echo "Generated at: $(date -Iseconds)"
    echo
    echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
    echo
    echo "## Checks"
    cat "${tmp_output}"
    echo
    echo "## Synthetic API Namespaces"
    kubectl get ns tenant-accounts tenant-payments tenant-cards tenant-customer-profile tenant-fraud tenant-open-banking --ignore-not-found=true || true
    echo
    echo "## Synthetic API Pods"
    kubectl get pods -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
    echo
    echo "## Synthetic API HTTPRoutes"
    kubectl get httproute -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  } >"${report}"
}

if ! kubectl version --client >/dev/null 2>&1 || ! kubectl cluster-info >/dev/null 2>&1; then
  echo "kubectl cannot reach a Kubernetes API server." | tee -a "${tmp_output}" >&2
  write_report "blocked"
  exit 1
fi

status="pass"
for entry in "${apis[@]}"; do
  read -r api namespace deployment route <<<"${entry}"
  if kubectl get namespace "${namespace}" >/dev/null 2>&1; then
    echo "${api} namespace: pass" | tee -a "${tmp_output}"
  else
    echo "${api} namespace: fail; missing ${namespace}" | tee -a "${tmp_output}" >&2
    status="fail"
  fi

  if kubectl -n "${namespace}" rollout status "deployment/${deployment}" --timeout=5s >/dev/null 2>&1; then
    echo "${api} deployment ready: pass" | tee -a "${tmp_output}"
  else
    echo "${api} deployment ready: fail; deployment/${deployment}" | tee -a "${tmp_output}" >&2
    status="fail"
  fi

  if kubectl -n "${namespace}" get "httproute/${route}" >/dev/null 2>&1; then
    echo "${api} HTTPRoute present: pass" | tee -a "${tmp_output}"
  else
    echo "${api} HTTPRoute present: fail; httproute/${route}" | tee -a "${tmp_output}" >&2
    status="fail"
  fi
done

write_report "${status}"
if [[ "${status}" != "pass" ]]; then
  exit 1
fi

echo "${report#${repo_root}/} generated."
