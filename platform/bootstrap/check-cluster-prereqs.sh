#!/usr/bin/env bash
set -euo pipefail

required_namespaces=(
  platform-system
  platform-gitops
  platform-security
  platform-networking
  platform-observability
  platform-identity
  tenant-accounts
  tenant-payments
  tenant-cards
  tenant-customer-profile
  tenant-fraud
  tenant-open-banking
  synthetic-clients
)

echo "Current context:"
kubectl config current-context

echo
echo "Kubernetes server version:"
kubectl version --short 2>/dev/null || kubectl version

echo
echo "API reachability:"
kubectl get --raw=/readyz >/dev/null
echo "readyz: ok"

echo
echo "Namespace status:"
for namespace in "${required_namespaces[@]}"; do
  if kubectl get namespace "$namespace" >/dev/null 2>&1; then
    echo "$namespace: present"
  else
    echo "$namespace: missing"
  fi
done

echo
echo "NetworkPolicy API support:"
if kubectl api-resources --api-group=networking.k8s.io | awk '{print $1}' | grep -qx networkpolicies; then
  echo "networkpolicies.networking.k8s.io: accepted by API server"
else
  echo "networkpolicies.networking.k8s.io: not reported by API server"
fi

echo
echo "Optional prerequisite namespaces:"
for namespace in cert-manager metallb-system; do
  if kubectl get namespace "$namespace" >/dev/null 2>&1; then
    echo "$namespace: present"
  else
    echo "$namespace: not applied"
  fi
done

echo
echo "Kong is intentionally not checked in goal 001."

