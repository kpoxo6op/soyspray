#!/usr/bin/env bash

# This script performs SSH checks in parallel, gathers additional info about Longhorn CRDs
# (volumes, replicas, engines), and includes a quick look at the default StorageClass.
# Steps and logs remain concise while providing deeper insight into Longhorn status.
#
# Usage: ./longhorn-health-check-v2.sh
#        ./longhorn-health-check-v2.sh --ssh-check
#
# It will gather information about the Longhorn installation in the cluster, including:
# - pods, deployments, CRDs
# - Longhorn volumes, replicas, engines
# - logs
# - optionally SSH into each node in parallel to check local disk config (e.g., /storage mount)

set -Eeuo pipefail

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
echo "Longhorn Health Check Script v2"
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
kubectl get nodes -o wide || true

echo
echo "5) Confirm CRDs for Longhorn exist..."
kubectl api-resources | grep -i longhorn || true

echo
echo "6) Checking logs of longhorn-manager pods (last 50 lines each)..."
kubectl logs -n "${LONGHORN_NAMESPACE}" -l app=longhorn-manager --tail=50 || true

echo
echo "7) Checking Longhorn volumes, replicas, and engines..."
kubectl -n "${LONGHORN_NAMESPACE}" get volumes.longhorn.io,replicas.longhorn.io,engines.longhorn.io 2>/dev/null || true

echo
echo "8) Checking StorageClasses for Longhorn default (if any)..."
kubectl get storageclasses | grep -i longhorn || echo "No Longhorn StorageClass found or no match."

if [[ "${DO_SSH_CHECK}" == "true" ]]; then
  echo
  echo "====================================================="
  echo "SSH checks in parallel for /storage or any needed Longhorn local config"
  echo "====================================================="

  # Define array of nodes
  nodes=("${WORKER_NODE1}" "${WORKER_NODE2}" "${WORKER_NODE3}" "${MASTER_NODE}")

  # Function for SSH checks
  function ssh_check() {
    local node_ip="$1"
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
  }

  # Run SSH checks in parallel
  for node_ip in "${nodes[@]}"; do
    ssh_check "${node_ip}" &
  done

  # Wait for all background processes
  wait
fi

echo
echo "====================================================="
echo "Summary of Longhorn Pod Readiness"
echo "====================================================="
ALL_READY=true
while read -r pod_line; do
  if [[ "$pod_line" == NAME* ]]; then
    continue
  fi
  POD_NAME=$(echo "$pod_line" | awk '{print $1}')
  READY_STATUS=$(echo "$pod_line" | awk '{print $2}')
  STATUS=$(echo "$pod_line" | awk '{print $3}')

  if [[ "$STATUS" != "Running" ]]; then
    echo "Pod $POD_NAME is NOT fully ready (status=$STATUS, ready=$READY_STATUS)"
    ALL_READY=false
  else
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
echo "Tip: ./longhorn-health-check-v2.sh > lh-check.txt"
echo "====================================================="
