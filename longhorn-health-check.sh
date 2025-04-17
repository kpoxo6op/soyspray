#!/usr/bin/env bash
#
# longhorn-health-check.sh
#
# Purpose:
#   Quickly gather Longhorn-related statuses from the cluster and optionally
#   SSH into each node to verify local disk config. Includes a brief summary
#   for overall health.
#
# Usage:
#   ./longhorn-health-check.sh
#   ./longhorn-health-check.sh --ssh-check
#
# Requirements:
#   - kubectl in PATH
#   - (optional) SSH access to each node
#
# Environment variables:
#   - K8S_USER (default: "ubuntu")
#   - WORKER_NODE1, WORKER_NODE2, WORKER_NODE3, MASTER_NODE
#     (If you want SSH checks, define these or set them inside the script.)

set -Eeuo pipefail

# Customize these if needed
LONGHORN_NAMESPACE="longhorn-system"
K8S_USER="${K8S_USER:-ubuntu}"

WORKER_NODE1="${WORKER_NODE1:-192.168.1.100}"
WORKER_NODE2="${WORKER_NODE2:-192.168.1.101}"
WORKER_NODE3="${WORKER_NODE3:-192.168.1.102}"
MASTER_NODE="${MASTER_NODE:-192.168.1.103}"

DO_SSH_CHECK="false"
if [[ "${1:-}" == "--ssh-check" ]]; then
  DO_SSH_CHECK="true"
fi

echo "====================================================="
echo "Longhorn Health Check Script"
echo "Namespace: ${LONGHORN_NAMESPACE}"
echo "====================================================="

echo
echo "1) Pods in ${LONGHORN_NAMESPACE} (wide output)..."
kubectl get pods -n "${LONGHORN_NAMESPACE}" -o wide || true

echo
echo "2) DaemonSets in ${LONGHORN_NAMESPACE}..."
kubectl get ds -n "${LONGHORN_NAMESPACE}" || true

echo
echo "3) Deployments in ${LONGHORN_NAMESPACE}..."
kubectl get deploy -n "${LONGHORN_NAMESPACE}" || true

echo
echo "4) Node info..."
# Removed label references (longhorn & node.longhorn.io/create-default-disk):
kubectl get nodes -o wide || true

echo
echo "5) Confirm CRDs for Longhorn exist..."
kubectl api-resources | grep -i longhorn || true

echo
echo "6) Checking logs of longhorn-manager pods (last 50 lines each)..."
kubectl logs -n "${LONGHORN_NAMESPACE}" -l app=longhorn-manager --tail=50 || true

if [[ "${DO_SSH_CHECK}" == "true" ]]; then
  echo
  echo "====================================================="
  echo "SSH checks for /storage or any needed Longhorn local config"
  echo "====================================================="
  for node_ip in "${WORKER_NODE1}" "${WORKER_NODE2}" "${WORKER_NODE3}" "${MASTER_NODE}"; do
    echo
    echo "--- SSH to ${node_ip} as ${K8S_USER} ---"
    ssh "${K8S_USER}@${node_ip}" <<NODECHECK || true
echo "[Node: ${node_ip}] df -h /storage (if present):"
df -h /storage 2>/dev/null || echo "/storage not mounted or not found."

echo "[Node: ${node_ip}] ls -ld /storage (if present):"
ls -ld /storage 2>/dev/null || echo "/storage dir not found."

echo "[Node: ${node_ip}] Checking kernel modules config (if relevant):"
ls /etc/modules-load.d/longhorn.conf 2>/dev/null || echo "No /etc/modules-load.d/longhorn.conf file."
NODECHECK
  done
fi

###############################
# Simple readiness check for pods
###############################
echo
echo "====================================================="
echo "Summary of Longhorn Pod Readiness"
echo "====================================================="
ALL_READY=true
while read -r pod_line; do
  # skip header line
  if [[ "$pod_line" == NAME* ]]; then
    continue
  fi
  # extract columns
  POD_NAME=$(echo "$pod_line" | awk '{print $1}')
  READY_STATUS=$(echo "$pod_line" | awk '{print $2}') # e.g. "1/1"
  STATUS=$(echo "$pod_line" | awk '{print $3}')       # e.g. "Running"

  # quick check: if READY != "Running" or some sub-container not ready
  if [[ "$STATUS" != "Running" ]] || [[ "$READY_STATUS" != */* ]]; then
    echo "Pod $POD_NAME is NOT fully ready (status=$STATUS, ready=$READY_STATUS)"
    ALL_READY=false
  else
    # if 2/2 or 3/3, etc, parse to compare
    WANTED=$(echo "$READY_STATUS" | cut -d'/' -f2)
    ACTUAL=$(echo "$READY_STATUS" | cut -d'/' -f1)
    if [[ "$ACTUAL" -lt "$WANTED" ]]; then
      echo "Pod $POD_NAME is partially ready: $READY_STATUS"
      ALL_READY=false
    fi
  fi
done < <(kubectl get pods -n "${LONGHORN_NAMESPACE}" 2>/dev/null || true)

if [[ "$ALL_READY" == "true" ]]; then
  echo "All Longhorn pods appear to be ready."
else
  echo "Some Longhorn pods are not fully ready; check details above."
fi

echo
echo "====================================================="
echo "Done. Output above should help diagnose Longhorn issues."
echo "Tip: ./longhorn-health-check.sh > lh-check.txt"
echo "====================================================="
