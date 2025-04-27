#hw.sh
#<<'COMMENT'
# Consolidated cluster inspection script.
#
# Key additions and changes
# -------------------------
# 1. Parallel execution:
#    • Uses GNU parallel if present, otherwise backgrounds jobs and waits.
#    • Concurrency is controlled with MAX_PARALLEL (default 4).
#
# 2. Lightweight / heavy toggle:
#    • Set SKIP_HEAVY=1 to skip lshw, iostat, parted, smartctl.
#
# 3. Argo CD status:
#    • Prints a one‑liner view of every Argo CD application (namespace argocd).
#
# 4. Comment‑free body:
#    • All explanatory text lives only in this header, per soyspray rules.
#
# Usage examples
# --------------
#   ./hw.sh                       # full run, default parallelism 4
#   MAX_PARALLEL=8 ./hw.sh        # higher concurrency
#   SKIP_HEAVY=1 ./hw.sh          # faster, omits heavy checks
#
# Requirements
# ------------
# • Bash 4+, kubectl context, SSH key‑based access as \$USER to each node.
# • GNU parallel optional (falls back automatically).
# COMMENT
#!/usr/bin/env bash
set -o pipefail

NODES=("192.168.1.100" "192.168.1.101" "192.168.1.102" "192.168.1.103")
USER="ubuntu"
MAX_PARALLEL=${MAX_PARALLEL:-4}
SKIP_HEAVY=${SKIP_HEAVY:-0}

run_parallel() {
  local fn=$1; shift
  if command -v parallel >/dev/null 2>&1; then
    parallel -j "$MAX_PARALLEL" "$fn" ::: "$@"
  else
    for n in "$@"; do "$fn" "$n" & done
    wait
  fi
}

hardware_node() {
  local node=$1
  echo "==============================================="
  echo "Gathering hardware information from node: $node"
  echo "==============================================="
  local cmds=(
    "hostname"
    "sudo lscpu"
    "sudo free -h"
    "sudo df -h /"
    "sudo lsblk -d -o NAME,SIZE,MODEL,ROTA"
    "sudo cat /proc/meminfo | grep -E 'MemTotal|SwapTotal'"
    "sudo nproc"
  )
  if [ "$SKIP_HEAVY" -eq 0 ]; then
    cmds+=("sudo lshw -short || true" "sudo iostat 1 1 || true")
  fi
  for c in "${cmds[@]}"; do
    echo "--- Running: $c ---"
    ssh -o StrictHostKeyChecking=no "$USER@$node" "$c" || echo "Failed: $c"
    echo "-------------------"
  done
  echo ""
}

gather_hardware_info() {
  echo "Starting hardware information gathering..."
  date
  echo ""
  run_parallel hardware_node "${NODES[@]}"
  echo "Hardware information gathering complete"
  date
  echo ""
}

k8s_load() {
  echo "========================================"
  echo "K8S HARDWARE LOAD & RESOURCE OVERVIEW"
  echo "========================================"
  echo ""
  echo "=== NODE LIST & STATUS ==="
  kubectl get nodes -o wide
  echo ""
  echo "=== NODE DETAILS (CAPACITY & ALLOCATED) ==="
  kubectl describe nodes | grep -A20 "Allocated resources" | grep -A8 "Resource"
  echo ""
  echo "=== POD DISTRIBUTION ANALYSIS ==="
  local total_pods
  total_pods=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
  local node_count
  node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
  if [ "$node_count" -eq 0 ]; then echo "No nodes found."; return; fi
  local tmp
  tmp=$(mktemp)
  kubectl get pods -A -o custom-columns="NODE:.spec.nodeName" --no-headers | sort | uniq -c | sort -nr >"$tmp"
  local max_pods min_pods avg_pods imbalance
  max_pods=$(head -1 "$tmp" | awk '{print $1}')
  min_pods=$(tail -1 "$tmp" | awk '{print $1}')
  if [ -z "$max_pods" ] || [ -z "$min_pods" ]; then echo "No running pods."; rm -f "$tmp"; return; fi
  avg_pods=$((total_pods / node_count))
  imbalance=$(( (max_pods - min_pods) * 100 / (max_pods>0?max_pods:1) ))
  echo "Total pods: $total_pods"
  echo "Average per node: $avg_pods"
  echo "Range: $min_pods – $max_pods"
  echo "Imbalance: $imbalance%"
  echo ""
  echo "PODS PER NODE:"
  cat "$tmp"
  rm -f "$tmp"
  echo ""
  echo "=== SCHEDULING PROBLEMS (first 10) ==="
  kubectl get pods -A | grep -vE "Running|Completed|Terminating|NAME" | head -10 || true
  echo ""
  echo "Recent eviction events (last 5):"
  kubectl get events -A --sort-by=.lastTimestamp 2>/dev/null | grep -iE "evict|drain" | tail -5 || true
  echo ""
}

storage_node() {
  local node=$1
  echo "==============================================="
  echo "Gathering STORAGE information from node: $node"
  echo "==============================================="
  local cmds=(
    "hostname"
    "sudo lsblk -f"
    "sudo fdisk -l"
    "sudo df -h"
    "sudo pvs"
    "sudo vgs"
    "sudo lvs"
    "echo '--- Local Storage Mounts ---' && sudo ls -l /mnt/disks/"
    "echo '--- Local PV Usage ---' && sudo df -h /mnt/disks/vol1"
  )
  if [ "$SKIP_HEAVY" -eq 0 ]; then
    cmds+=("sudo parted -l || true" "sudo smartctl -H /dev/sda || true")
  fi
  for c in "${cmds[@]}"; do
    echo "--- Running: $c ---"
    ssh -o StrictHostKeyChecking=no "$USER@$node" "$c" || echo "Failed: $c"
    echo "-------------------"
  done
  echo ""
}

gather_storage_info() {
  echo "Starting storage information gathering..."
  date
  echo ""
  run_parallel storage_node "${NODES[@]}"
  echo "Storage information gathering complete"
  date
  echo ""
}

argo_status() {
  echo "========================================"
  echo "ARGO CD APPLICATION STATUS"
  echo "========================================"
  if kubectl get ns argocd >/dev/null 2>&1; then
    kubectl -n argocd get applications -o wide
  else
    echo "Argo CD namespace not found."
  fi
  echo ""
}

gather_hardware_info
k8s_load
gather_storage_info
argo_status
echo "All information gathering steps are complete."
