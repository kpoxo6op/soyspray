#!/usr/bin/env bash
set -Eeuo pipefail

NODES=("192.168.1.100" "192.168.1.101" "192.168.1.102" "192.168.1.103")
USER="ubuntu"
MAX_PARALLEL=${MAX_PARALLEL:-4}
SKIP_HEAVY=${SKIP_HEAVY:-0}

LONGHORN_NAMESPACE="longhorn-system"
DO_SSH_CHECK="false"
if [[ "${1:-}" == "--ssh-check" ]]; then
  DO_SSH_CHECK="true"
fi

# Runs jobs in parallel but prints outputs in the order they were started.
# This is more portable than using 'wait -n' (which doesn't exist in old Bash).
run_parallel_in_order() {
  local fn=$1
  shift
  local outputs=()
  local pids=()

  # Launch each job in the background, store PID and temp file.
  for node in "$@"; do
    local tmp
    tmp=$(mktemp)
    outputs+=("$tmp:$node")
    (
      "$fn" "$node" >"$tmp" 2>&1
    ) &
    pids+=($!)
  done

  # Wait for jobs in the same order, then print each job's output.
  for i in "${!pids[@]}"; do
    wait "${pids[i]}" || true
    local pair="${outputs[i]}"
    local tmp="${pair%%:*}"
    local node="${pair##*:}"
    cat "$tmp"
    rm -f "$tmp"
  done
}

hardware_node() {
  echo "==============================================="
  echo "Gathering hardware information from node: $1"
  echo "==============================================="
  ssh -o StrictHostKeyChecking=no "$USER@$1" "hostname"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo lscpu"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo free -h"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo df -h /"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo lsblk -d -o NAME,SIZE,MODEL,ROTA"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo cat /proc/meminfo | grep -E 'MemTotal|SwapTotal'"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo nproc"
  if [ "$SKIP_HEAVY" -eq 0 ]; then
    ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo lshw -short || true"
    ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo iostat 1 1 || true"
  fi
}

gather_hardware_info() {
  echo "Starting hardware information gathering..."
  date
  run_parallel_in_order hardware_node "${NODES[@]}"
  echo "Hardware information gathering complete"
  date
  echo
}

k8s_load() {
  echo "========================================"
  echo "K8S HARDWARE LOAD & RESOURCE OVERVIEW"
  echo "========================================"
  echo
  echo "=== NODE LIST & STATUS ==="
  kubectl get nodes -o wide
  echo
  echo "=== NODE DETAILS (CAPACITY & ALLOCATED) ==="
  kubectl describe nodes | grep -A20 "Allocated resources" | grep -A8 "Resource"
  echo
  echo "=== POD DISTRIBUTION ANALYSIS ==="
  local total_pods
  total_pods=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
  local node_count
  node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
  if [ "$node_count" -eq 0 ]; then
    echo "No nodes found."
    return
  fi
  local tmp
  tmp=$(mktemp)
  kubectl get pods -A -o custom-columns="NODE:.spec.nodeName" --no-headers | sort | uniq -c | sort -nr >"$tmp"
  local max_pods min_pods avg_pods imbalance
  max_pods=$(head -1 "$tmp" | awk '{print $1}')
  min_pods=$(tail -1 "$tmp" | awk '{print $1}')
  if [ -z "$max_pods" ] || [ -z "$min_pods" ]; then
    echo "No running pods."
    rm -f "$tmp"
    return
  fi
  avg_pods=$((total_pods / node_count))
  imbalance=$(( (max_pods - min_pods) * 100 / (max_pods>0?max_pods:1) ))
  echo "Total pods: $total_pods"
  echo "Average per node: $avg_pods"
  echo "Range: $min_pods – $max_pods"
  echo "Imbalance: $imbalance%"
  echo
  echo "PODS PER NODE:"
  cat "$tmp"
  rm -f "$tmp"
  echo
  echo "=== SCHEDULING PROBLEMS (first 10) ==="
  kubectl get pods -A | grep -vE "Running|Completed|Terminating|NAME" | head -10 || true
  echo
  echo "Recent eviction events (last 5):"
  kubectl get events -A --sort-by=.lastTimestamp 2>/dev/null | grep -iE "evict|drain" | tail -5 || true
  echo
}

storage_node() {
  echo "==============================================="
  echo "Gathering STORAGE information from node: $1"
  echo "==============================================="
  ssh -o StrictHostKeyChecking=no "$USER@$1" "hostname"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo lsblk -f"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo fdisk -l"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo df -h"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo pvs"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo vgs"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo lvs"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo ls -l /mnt/disks/ || true"
  ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo df -h /mnt/disks/vol1 || true"
  if [ "$SKIP_HEAVY" -eq 0 ]; then
    ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo parted -l || true"
    ssh -o StrictHostKeyChecking=no "$USER@$1" "sudo smartctl -H /dev/sda || true"
  fi
}

gather_storage_info() {
  echo "Starting storage information gathering..."
  date
  run_parallel_in_order storage_node "${NODES[@]}"
  echo "Storage information gathering complete"
  date
  echo
}

argo_status() {
  echo "========================================"
  echo "ARGO CD APPLICATION STATUS"
  echo "========================================"
  if kubectl get ns argocd >/dev/null 2>&1; then
    kubectl -n argocd get applications -o wide
  else
    echo "Argo CD namespace not found."
  fi
  echo
}

longhorn_check() {
  echo "====================================================="
  echo "Longhorn Health Check"
  echo "====================================================="
  kubectl get pods -n "${LONGHORN_NAMESPACE}" -o wide || true
  echo
  kubectl get ds -n "${LONGHORN_NAMESPACE}" || true
  echo
  kubectl get deploy -n "${LONGHORN_NAMESPACE}" || true
  echo
  kubectl get nodes -o wide || true
  echo
  kubectl api-resources | grep -i longhorn || true
  echo
  kubectl logs -n "${LONGHORN_NAMESPACE}" -l app=longhorn-manager --tail=50 || true
  echo
  kubectl -n "${LONGHORN_NAMESPACE}" get volumes.longhorn.io,replicas.longhorn.io,engines.longhorn.io 2>/dev/null || true
  echo
  kubectl get storageclasses | grep -i longhorn || echo "No Longhorn StorageClass found or no match."
  if [[ "$DO_SSH_CHECK" == "true" ]]; then
    echo
    echo "====================================================="
    echo "SSH checks in parallel for /storage or relevant config"
    echo "====================================================="
    function ssh_checks_in_order() {
      local node_ip="$1"
      local tmp
      tmp=$(mktemp)
      {
        echo
        echo "--- SSH to $node_ip as $USER ---"
        ssh -o StrictHostKeyChecking=no "$USER@$node_ip" "
          echo '[Node: $node_ip] df -h /storage (if present):'
          df -h /storage 2>/dev/null || echo '/storage not mounted or not found.'
          echo '[Node: $node_ip] ls -ld /storage (if present):'
          ls -ld /storage 2>/dev/null || echo '/storage dir not found.'
          ls /etc/modules-load.d/longhorn.conf 2>/dev/null || echo 'No /etc/modules-load.d/longhorn.conf file.'
        "
      } > "$tmp" 2>&1
      cat "$tmp"
      rm -f "$tmp"
    }
    run_parallel_in_order ssh_checks_in_order "${NODES[@]}"
  fi
  echo
  echo "====================================================="
  echo "Summary of Longhorn Pod Readiness"
  echo "====================================================="
  local all_ready=true
  while read -r pod_line; do
    if [[ "$pod_line" == NAME* ]]; then
      continue
    fi
    local pod_name
    pod_name=$(echo "$pod_line" | awk '{print $1}')
    local ready_status
    ready_status=$(echo "$pod_line" | awk '{print $2}')
    local status
    status=$(echo "$pod_line" | awk '{print $3}')
    if [[ "$status" != "Running" ]]; then
      echo "Pod $pod_name is NOT fully ready (status=$status, ready=$ready_status)"
      all_ready=false
    else
      local wanted
      local actual
      wanted=$(echo "$ready_status" | cut -d'/' -f2)
      actual=$(echo "$ready_status" | cut -d'/' -f1)
      if [[ "$actual" -lt "$wanted" ]]; then
        echo "Pod $pod_name is partially ready: $ready_status"
        all_ready=false
      fi
    fi
  done < <(kubectl get pods -n "$LONGHORN_NAMESPACE" 2>/dev/null || true)
  if [[ "$all_ready" == "true" ]]; then
    echo "All Longhorn pods appear to be ready."
  else
    echo "Some Longhorn pods are not fully ready; check details above."
  fi
  echo
  echo "====================================================="
  echo "Done. Output above should help diagnose Longhorn issues."
  echo "====================================================="
}

longhorn_storage_mount_check_node() {
  echo "==============================================="
  echo "Longhorn Storage Mount Check for node: $1"
  echo "==============================================="
  ssh -o StrictHostKeyChecking=no "$USER@$1" bash <<'EOF'
echo "Hostname: $(hostname)"
echo
echo "lsblk -f:"
lsblk -f
echo
echo "df -h /storage (if present):"
df -h /storage 2>/dev/null || echo "/storage not mounted"
echo
echo "ls -ld /storage:"
ls -ld /storage 2>/dev/null || echo "/storage dir not found"
echo
echo "mount | grep /storage:"
mount | grep /storage || echo "/storage not a mount point"
echo
echo "cat /etc/fstab | grep storage:"
cat /etc/fstab | grep storage || echo "No /storage entry in fstab"
echo
echo "Longhorn disk directories (if any):"
ls -l /var/lib/longhorn 2>/dev/null || echo "/var/lib/longhorn not found"
EOF
}

longhorn_storage_mount_check() {
  echo "==== Longhorn Storage Mount Check (all nodes) ===="
  run_parallel_in_order longhorn_storage_mount_check_node "${NODES[@]}"
  echo
  echo "==== Longhorn Disk CRs (from cluster) ===="
  kubectl get disks.longhorn.io -A -o wide 2>/dev/null || echo "No Longhorn disk CRs found"
  echo
  echo "==== SUMMARY ===="
  echo "For each node above, check:"
  echo "- If /storage is a mount point for your SSD/NVMe (see 'mount' and 'df -h /storage')"
  echo "- If /storage is missing or just a directory, Longhorn will use the root disk (eMMC)"
  echo "- If /var/lib/longhorn exists, Longhorn may use it if /storage is not mounted"
  echo "- Fix /etc/fstab and remount if needed, then remove/add disks in Longhorn UI"
}

gather_hardware_info
k8s_load
gather_storage_info
argo_status
longhorn_check
longhorn_storage_mount_check
echo "All checks complete."
