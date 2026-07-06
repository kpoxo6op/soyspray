#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
report="${repo_root}/reports/synthetic-api-runtime-state.md"

{
  echo "# Synthetic API Runtime State"
  echo
  echo "Status: collected"
  echo
  echo "Generated at: $(date -Iseconds)"
  echo
  echo "Kubernetes context: $(kubectl config current-context 2>/dev/null || true)"
  echo
  echo "## Tenant Namespaces"
  kubectl get ns tenant-accounts tenant-payments tenant-cards tenant-customer-profile tenant-fraud tenant-open-banking --ignore-not-found=true || true
  echo
  echo "## Deployments"
  kubectl get deploy -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  echo
  echo "## Pods"
  kubectl get pods -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  echo
  echo "## Services"
  kubectl get svc -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  echo
  echo "## ConfigMaps"
  kubectl get configmap -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  echo
  echo "## HTTPRoutes"
  kubectl get httproute -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  echo
  echo "## NetworkPolicies"
  kubectl get networkpolicy -A -l banklab.konghq.com/platform-layer=synthetic-api --ignore-not-found=true || true
  echo
  echo "## Gateway API"
  kubectl get gatewayclass kong -o wide 2>/dev/null || true
  kubectl -n platform-kong get gateway kong-internal kong-external -o wide 2>/dev/null || true
  echo
  echo "## Kong Services"
  kubectl -n platform-kong get svc banklab-kong-gateway-proxy banklab-kong-admin -o wide 2>/dev/null || true
} >"${report}"

echo "${report#${repo_root}/} generated."
