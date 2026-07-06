#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
report="${KONG_RUNTIME_EVIDENCE_REPORT:-${repo_root}/reports/kong-runtime-evidence.md}"
mkdir -p "$(dirname "${report}")"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required to collect runtime evidence." >&2
  exit 1
fi

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "${context}" ]]; then
  echo "No Kubernetes context configured." >&2
  exit 1
fi

{
  echo "# Kong Runtime Evidence"
  echo
  echo "Generated at: $(date --iso-8601=seconds)"
  echo
  echo "Kubernetes context: ${context}"
  echo
  echo "## Namespaces"
  kubectl get namespace platform-kong platform-kong-smoke --ignore-not-found=true
  echo
  echo "## Kong Pods"
  kubectl -n platform-kong get pods --show-labels --ignore-not-found=true
  echo
  echo "## Kong Services"
  kubectl -n platform-kong get service --ignore-not-found=true
  echo
  echo "## Kong Secret Names"
  kubectl -n platform-kong get secret --ignore-not-found=true
  echo
  echo "## GatewayClass"
  kubectl get gatewayclass kong --ignore-not-found=true
  echo
  echo "## Gateways"
  kubectl -n platform-kong get gateway --ignore-not-found=true
  echo
  echo "## HTTPRoutes"
  kubectl -n platform-kong-smoke get httproute --ignore-not-found=true
  echo
  echo "## GatewayClass Description"
  kubectl describe gatewayclass kong 2>/dev/null || true
  echo
  echo "## Gateway Description"
  kubectl -n platform-kong describe gateway 2>/dev/null || true
  echo
  echo "## HTTPRoute Description"
  kubectl -n platform-kong-smoke describe httproute 2>/dev/null || true
  echo
  echo "## KIC Logs"
  kubectl -n platform-kong logs -l app.kubernetes.io/name=controller --tail=120 2>/dev/null || true
} >"${report}"

echo "${report#${repo_root}/} generated."
