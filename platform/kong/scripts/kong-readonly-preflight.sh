#!/usr/bin/env bash
set -euo pipefail

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found. Optional Kong read-only preflight not run."
  exit 0
fi

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "${context}" ]]; then
  echo "No Kubernetes context configured. Optional Kong read-only preflight not run."
  exit 0
fi

echo "Current Kubernetes context: ${context}"
echo
if ! kubectl get namespace platform-kong >/dev/null 2>&1; then
  echo "Kong baseline not applied yet: namespace platform-kong is absent."
  exit 0
fi

echo "Kong namespace:"
kubectl get namespace platform-kong
echo
echo "Kong pods:"
kubectl -n platform-kong get pods --show-labels
echo
echo "Kong proxy service:"
kubectl -n platform-kong get service banklab-kong-gateway-proxy --ignore-not-found=true
echo
echo "Admin services, if present:"
kubectl -n platform-kong get service --ignore-not-found=true | grep -i admin || true
echo
echo "GatewayClass and Gateways:"
kubectl get gatewayclass kong --ignore-not-found=true
kubectl -n platform-kong get gateway --ignore-not-found=true
echo
echo "Smoke resources if present:"
kubectl get namespace platform-kong-smoke --ignore-not-found=true
kubectl -n platform-kong-smoke get deployment,service --ignore-not-found=true
kubectl -n platform-kong-smoke get httproute --ignore-not-found=true
