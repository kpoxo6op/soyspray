#!/usr/bin/env bash
set -euo pipefail

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found. Optional read-only cluster preflight not run."
  exit 0
fi

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "${context}" ]]; then
  echo "No Kubernetes context configured. Optional read-only cluster preflight not run."
  exit 0
fi

echo "Current Kubernetes context: ${context}"
echo
echo "kubectl client:"
kubectl version --client=true
echo
echo "Kubernetes API readyz:"
kubectl get --raw=/readyz 2>/dev/null || echo "API readyz not reachable."
echo
echo "API resources containing Gateway, NetworkPolicy, or Ingress:"
kubectl api-resources 2>/dev/null | grep -E 'gateway|httproute|networkpolicies|ingress' || true
echo
echo "Known platform namespaces if present:"
kubectl get namespace platform-kong platform-kong-smoke metallb-system cert-manager --ignore-not-found=true
echo
echo "Gateway API CRDs if present:"
kubectl get crd gatewayclasses.gateway.networking.k8s.io gateways.gateway.networking.k8s.io httproutes.gateway.networking.k8s.io --ignore-not-found=true
echo
echo "Can this identity read namespaces?"
kubectl auth can-i get namespaces || true
