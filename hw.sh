#!/usr/bin/env bash
#
# hw.sh - Consolidated script for:
#   1) Hardware Info via SSH (sudo)
#   2) K8S Hardware Load (local kubectl)
#   3) Storage Info via SSH (sudo)
#
# This script runs locally as a normal user.
# It uses 'ssh ubuntu@...' and 'sudo' on each remote node
# for privileged commands (lshw, iostat, parted, smartctl, etc.).

set -o pipefail

############################################################
# Common Variables
############################################################

# Nodes to SSH into for hardware/storage checks
NODES=("192.168.1.100" "192.168.1.101" "192.168.1.102" "192.168.1.103")
USER="ubuntu"

############################################################
# 1) HARDWARE INFO
############################################################
function gather_hardware_info() {
  #
  # Using sudo on each remote node so no warnings about privileges.
  #
  local hardware_commands=(
    "hostname"
    "sudo lscpu"
    "sudo free -h"
    "sudo df -h /"
    "sudo lsblk -d -o NAME,SIZE,MODEL,ROTA"
    "sudo cat /proc/meminfo | grep -E 'MemTotal|SwapTotal'"
    "sudo nproc"
    "sudo lshw -short || echo '[INFO] lshw not installed or insufficient privileges.'"
    "sudo iostat 1 1 || echo '[INFO] iostat (sysstat) not installed or insufficient privileges.'"
  )

  echo "Starting hardware information gathering..."
  echo "$(date)"
  echo ""

  for node in "${NODES[@]}"; do
    echo "==============================================="
    echo "Gathering hardware information from node: $node"
    echo "==============================================="
    for cmd in "${hardware_commands[@]}"; do
      echo ""
      echo "--- Running: $cmd ---"
      ssh -o StrictHostKeyChecking=no "$USER@$node" "$cmd" || echo "Failed to run $cmd"
      echo "-------------------"
    done
    echo ""
  done

  echo "Hardware information gathering complete"
  echo "$(date)"
  echo ""
}

############################################################
# 2) K8S HARDWARE LOAD
############################################################
function gather_k8s_hardware_load() {
  echo "========================================"
  echo " K8S HARDWARE LOAD & RESOURCE OVERVIEW"
  echo "========================================"

  # 1) Basic Node Info
  echo ""
  echo "=== NODE LIST & STATUS ==="
  kubectl get nodes -o wide

  echo ""
  echo "=== NODE DETAILS (CAPACITY & ALLOCATED) ==="
  kubectl describe nodes | grep -A 20 "Allocated resources" | grep -A 8 "Resource"

  # 2) Pod Distribution
  echo ""
  echo "=== POD DISTRIBUTION ANALYSIS ==="

  TOTAL_PODS=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
  NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
  if [ "$NODE_COUNT" -eq 0 ]; then
    echo "No nodes found. Exiting."
    return
  fi

  TEMP_FILE=$(mktemp)
  kubectl get pods -A \
    -o custom-columns="NODE:.spec.nodeName" \
    --no-headers \
    | sort \
    | uniq -c \
    | sort -nr > "$TEMP_FILE"

  MAX_PODS=$(head -1 "$TEMP_FILE" | awk '{print $1}')
  MIN_PODS=$(tail -1 "$TEMP_FILE" | awk '{print $1}')

  if [ -z "$MAX_PODS" ] || [ -z "$MIN_PODS" ]; then
    echo "No running pods found or unable to parse distribution."
    rm -f "$TEMP_FILE"
    return
  fi

  AVG_PODS=$((TOTAL_PODS / NODE_COUNT))
  IMBALANCE_PERCENT=$(( (MAX_PODS - MIN_PODS) * 100 / (MAX_PODS > 0 ? MAX_PODS : 1) ))

  echo "Total pods in cluster: $TOTAL_PODS"
  echo "Average pods per node: $AVG_PODS"
  echo "Pod count range: $MIN_PODS - $MAX_PODS"
  echo "Imbalance: $IMBALANCE_PERCENT%"

  if [ "$IMBALANCE_PERCENT" -gt 30 ]; then
    echo "WARNING: High imbalance detected (~$IMBALANCE_PERCENT%). Consider rebalancing."
  elif [ "$IMBALANCE_PERCENT" -gt 15 ]; then
    echo "NOTICE: Moderate imbalance detected (~$IMBALANCE_PERCENT%)."
  else
    echo "OK: Cluster appears reasonably balanced."
  fi

  echo ""
  echo "PODS PER NODE:"
  cat "$TEMP_FILE"
  rm -f "$TEMP_FILE"

  # 3) Resource Requests by Namespace
  echo ""
  echo "=== RESOURCE REQUESTS (BY NAMESPACE) ==="
  for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | sort); do
    NS_POD_COUNT=$(kubectl get pods -n "$ns" --no-headers 2>/dev/null | wc -l | xargs)
    if [ "$NS_POD_COUNT" -gt 0 ]; then
      echo ""
      echo "Namespace: $ns (Pods: $NS_POD_COUNT)"
      kubectl -n "$ns" get pods \
        -o custom-columns="NAME:.metadata.name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory,NODE:.spec.nodeName" \
        2>/dev/null | head -15
      if [ "$NS_POD_COUNT" -gt 15 ]; then
        echo "... and $((NS_POD_COUNT - 15)) more pods in $ns"
      fi
    fi
  done

  # 4) Scheduling Constraints & Problems
  echo ""
  echo "=== SCHEDULING CONSTRAINTS ==="
  echo "Nodes with taints:"
  kubectl get nodes -o json 2>/dev/null \
    | jq -r '.items[] | select(.spec.taints) | .metadata.name + ": " + (.spec.taints[] | .key + "=" + .value + ":" + .effect)' \
    || echo "No taints found (or jq not installed)."

  echo ""
  echo "Pods with node affinity/anti-affinity (first 10):"
  kubectl get pods -A -o json 2>/dev/null \
    | jq -r '.items[] | select(.spec.affinity.nodeAffinity) | .metadata.namespace + "/" + .metadata.name' \
    | head -10 \
    || echo "None found (or jq not installed)."

  echo ""
  echo "Pods with pod affinity/anti-affinity (first 10):"
  kubectl get pods -A -o json 2>/dev/null \
    | jq -r '.items[] | select(.spec.affinity.podAffinity or .spec.affinity.podAntiAffinity) | .metadata.namespace + "/" + .metadata.name' \
    | head -10 \
    || echo "None found (or jq not installed)."

  echo ""
  echo "DaemonSets (run on every eligible node):"
  kubectl get ds -A

  echo ""
  echo "=== SCHEDULING PROBLEMS ==="
  echo "Pods not Running/Completed (first 10):"
  kubectl get pods -A | grep -vE "Running|Completed|Terminating|NAME" | head -10 || echo "None found."

  echo ""
  echo "Recent eviction events (last 5):"
  kubectl get events -A --sort-by=.lastTimestamp 2>/dev/null | grep -iE "evict|drain" | tail -5 || echo "No recent eviction events."

  # 5) Node Status & Optional collectl
  echo ""
  echo "=== NODE STATUS CONDITIONS ==="
  kubectl get nodes -o custom-columns="NODE:.metadata.name,CONDITIONS:.status.conditions[*].type"

  # If collectl is installed locally and we can SSH as ubuntu with passwordless sudo, let's run a quick snapshot
  if command -v collectl >/dev/null 2>&1; then
    echo ""
    echo "=== COLLECTL NODE-LEVEL METRICS ==="
    for node in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do
      echo ""
      echo "Node: $node"
      echo "---------------------------"
      ssh "$USER@$node" "sudo collectl -scmd --count 1 2>/dev/null" || echo "Could not run collectl on $node."
    done
  else
    echo ""
    echo "Skipping collectl gathering: collectl not found on local system."
  fi

  # 6) Rebalancing Recommendations
  echo ""
  echo "=== REBALANCING RECOMMENDATIONS ==="
  if [ "$IMBALANCE_PERCENT" -gt 20 ]; then
    echo "Consider rebalancing the cluster. High imbalance of ~$IMBALANCE_PERCENT%."

    echo "Nodes with most pods (candidates for draining):"
    kubectl get pods -A \
      -o custom-columns="NODE:.spec.nodeName" \
      --no-headers \
      | sort \
      | uniq -c \
      | sort -nr \
      | head -3

    echo ""
    echo "Nodes with fewest pods (candidates for scheduling new pods):"
    kubectl get pods -A \
      -o custom-columns="NODE:.spec.nodeName" \
      --no-headers \
      | sort \
      | uniq -c \
      | sort -n \
      | head -3

    echo ""
    echo "If using Ansible + Kubespray, example rebalance command might be:"
    TOP_NODE=$(
      kubectl get pods -A \
        -o custom-columns="NODE:.spec.nodeName" \
        --no-headers \
        | sort \
        | uniq -c \
        | sort -nr \
        | head -1 \
        | awk '{print $2}'
    )
    echo "  ansible-playbook -i <inventory> <rebalance-playbook.yml> \\"
    echo "    -e \"skip_confirmation=true\" -e \"single_node=$TOP_NODE\""
  else
    echo "No severe imbalance detected. Imbalance at ~$IMBALANCE_PERCENT%. Rebalancing not urgent."
  fi

  echo ""
  echo "Done. Review the results above for potential issues."
  echo ""
}

############################################################
# 3) STORAGE INFO
############################################################
function gather_storage_info() {
  #
  # Using sudo on each remote node for parted, smartctl, etc.
  #
  local storage_commands=(
    "hostname"
    "sudo lsblk -f"
    "sudo fdisk -l"
    "sudo df -h"
    "sudo pvs"
    "sudo vgs"
    "sudo lvs"
    "echo '--- Local Storage Mounts ---' && sudo ls -l /mnt/disks/"
    "echo '--- Local PV Usage ---' && sudo df -h /mnt/disks/vol1"

    "sudo parted -l || echo '[INFO] parted not installed or insufficient privileges.'"
    "sudo smartctl -H /dev/sda || echo '[INFO] smartctl or /dev/sda not found.'"
  )

  echo "Starting storage information gathering..."
  echo "$(date)"
  echo ""

  for node in "${NODES[@]}"; do
    echo "==============================================="
    echo "Gathering STORAGE information from node: $node"
    echo "==============================================="
    for cmd in "${storage_commands[@]}"; do
      echo ""
      echo "--- Running: $cmd ---"
      ssh -o StrictHostKeyChecking=no "$USER@$node" "$cmd" || echo "Failed to run $cmd"
      echo "-------------------"
    done
    echo ""
  done

  echo "Storage information gathering complete"
  echo "$(date)"
  echo ""
}

############################################################
# MAIN SCRIPT
############################################################

# 1) Hardware Info
gather_hardware_info

# 2) K8S HARDWARE LOAD
gather_k8s_hardware_load

# 3) Storage Info
gather_storage_info

echo "All information gathering steps are complete."
