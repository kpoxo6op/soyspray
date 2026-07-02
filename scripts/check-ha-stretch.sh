#!/usr/bin/env bash
#
# Validate the soyspray one-node-loss stretch.
#
# Repo mode checks the Kubespray inventory and HA variables.
# Live mode also checks the current Kubernetes and etcd state.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTORY="${ROOT_DIR}/kubespray/inventory/soycluster/hosts.yml"
DEFAULT_VIP="192.168.20.13"
EXPECTED_NODES=(node-0 node-1 node-2)
declare -A NODE_IPS=(
  [node-0]="192.168.20.10"
  [node-1]="192.168.20.11"
  [node-2]="192.168.20.12"
)

expect="ha"
repo_only=false
live=false
vip="${DEFAULT_VIP}"
failures=0
inventory_json=""

usage() {
  cat <<'EOF'
Usage:
  scripts/check-ha-stretch.sh [--expect-current|--expect-ha] [--repo-only|--live] [--vip IP]

Examples:
  scripts/check-ha-stretch.sh --expect-current --repo-only
  scripts/check-ha-stretch.sh --expect-ha --repo-only
  scripts/check-ha-stretch.sh --expect-ha --live --vip 192.168.20.13
EOF
}

note_ok() {
  printf 'ok - %s\n' "$1"
}

note_fail() {
  printf 'not ok - %s\n' "$1" >&2
  failures=$((failures + 1))
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    note_fail "missing required command: $1"
    return 1
  fi
}

ansible_inventory_cmd() {
  if [[ -n "${ANSIBLE_INVENTORY:-}" ]]; then
    printf '%s\n' "${ANSIBLE_INVENTORY}"
  elif [[ -x "${ROOT_DIR}/soyspray-venv/bin/ansible-inventory" ]]; then
    printf '%s\n' "${ROOT_DIR}/soyspray-venv/bin/ansible-inventory"
  elif command -v ansible-inventory >/dev/null 2>&1; then
    command -v ansible-inventory
  else
    return 1
  fi
}

jq_inventory() {
  jq -e "$@" <<<"${inventory_json}" >/dev/null
}

jq_inventory_value() {
  jq -r "$@" <<<"${inventory_json}"
}

json_array_from_args() {
  printf '%s\n' "$@" | jq -R . | jq -sc 'sort'
}

expect_group_hosts() {
  local group="$1"
  shift
  local expected actual
  expected="$(json_array_from_args "$@")"
  actual="$(jq -c --arg group "${group}" '[.[$group].hosts[]] | sort' <<<"${inventory_json}")"

  if [[ "${actual}" == "${expected}" ]]; then
    note_ok "inventory group ${group} has hosts ${expected}"
  else
    note_fail "inventory group ${group} has ${actual}, expected ${expected}"
  fi
}

expect_host_ip() {
  local node="$1"
  local expected_ip="$2"
  local actual_ip
  actual_ip="$(jq_inventory_value --arg node "${node}" '._meta.hostvars[$node].ip // empty')"

  if [[ "${actual_ip}" == "${expected_ip}" ]]; then
    note_ok "inventory ${node} ip is ${expected_ip}"
  else
    note_fail "inventory ${node} ip is ${actual_ip:-<missing>}, expected ${expected_ip}"
  fi
}

expect_host_label() {
  local node="$1"
  local label="$2"
  local expected="$3"

  if jq_inventory --arg node "${node}" --arg label "${label}" --arg expected "${expected}" \
    '._meta.hostvars[$node].node_labels[$label] == $expected'; then
    note_ok "inventory ${node} label ${label}=${expected}"
  else
    note_fail "inventory ${node} label ${label} is not ${expected}"
  fi
}

expect_var_bool() {
  local var="$1"
  local expected="$2"

  if jq_inventory --arg var "${var}" --argjson expected "${expected}" \
    '._meta.hostvars["node-0"][$var] == $expected'; then
    note_ok "inventory var ${var}=${expected}"
  else
    local actual
    actual="$(jq_inventory_value --arg var "${var}" '._meta.hostvars["node-0"][$var] // "<missing>"')"
    note_fail "inventory var ${var} is ${actual}, expected ${expected}"
  fi
}

expect_var_string() {
  local var="$1"
  local expected="$2"

  if jq_inventory --arg var "${var}" --arg expected "${expected}" \
    '._meta.hostvars["node-0"][$var] == $expected'; then
    note_ok "inventory var ${var}=${expected}"
  else
    local actual
    actual="$(jq_inventory_value --arg var "${var}" '._meta.hostvars["node-0"][$var] // "<missing>"')"
    note_fail "inventory var ${var} is ${actual}, expected ${expected}"
  fi
}

expect_var_int_at_least() {
  local var="$1"
  local minimum="$2"

  if jq_inventory --arg var "${var}" --argjson minimum "${minimum}" \
    '._meta.hostvars["node-0"][$var] != null and (._meta.hostvars["node-0"][$var] | tonumber) >= $minimum'; then
    note_ok "inventory var ${var} is at least ${minimum}"
  else
    local actual
    actual="$(jq_inventory_value --arg var "${var}" '._meta.hostvars["node-0"][$var] // "<missing>"')"
    note_fail "inventory var ${var} is ${actual}, expected at least ${minimum}"
  fi
}

load_inventory() {
  local inventory_bin
  inventory_bin="$(ansible_inventory_cmd)" || {
    note_fail "missing ansible-inventory; run make venv or activate soyspray-venv"
    return 1
  }

  inventory_json="$("${inventory_bin}" -i "${INVENTORY}" --list)"
}

check_repo_common() {
  need_cmd jq || true
  load_inventory || return 0

  expect_group_hosts kube_node "${EXPECTED_NODES[@]}"

  for node in "${EXPECTED_NODES[@]}"; do
    expect_host_ip "${node}" "${NODE_IPS[$node]}"
    expect_host_label "${node}" "node-role.kubernetes.io/worker" "true"
    expect_host_label "${node}" "soyspray.vip/longhorn-ssd" "true"
  done

  expect_host_label node-0 "soyspray.vip/local-media" "true"
  expect_var_bool kube_proxy_strict_arp true
}

check_repo_current() {
  check_repo_common
  expect_group_hosts kube_control_plane node-0
  expect_group_hosts etcd node-0
  expect_var_bool kube_vip_enabled false
}

check_repo_ha() {
  check_repo_common
  expect_group_hosts kube_control_plane "${EXPECTED_NODES[@]}"
  expect_group_hosts etcd "${EXPECTED_NODES[@]}"
  expect_var_bool kube_vip_enabled true
  expect_var_bool kube_vip_arp_enabled true
  expect_var_bool kube_vip_controlplane_enabled true
  expect_var_bool kube_vip_services_enabled false
  expect_var_string kube_vip_address "${vip}"
  expect_var_int_at_least dns_min_replicas 2

  if jq_inventory --arg vip "${vip}" \
    '._meta.hostvars["node-0"].loadbalancer_apiserver.address == $vip and (._meta.hostvars["node-0"].loadbalancer_apiserver.port | tonumber) == 6443'; then
    note_ok "inventory loadbalancer_apiserver points at ${vip}:6443"
  else
    local actual
    actual="$(jq_inventory_value '._meta.hostvars["node-0"].loadbalancer_apiserver // "<missing>"')"
    note_fail "inventory loadbalancer_apiserver is ${actual}, expected ${vip}:6443"
  fi
}

kubectl_json() {
  kubectl "$@" -o json
}

check_live_node_ready() {
  local node="$1"
  if kubectl_json get node "${node}" | jq -e \
    'any(.status.conditions[]; .type == "Ready" and .status == "True")' >/dev/null; then
    note_ok "live node ${node} is Ready"
  else
    note_fail "live node ${node} is not Ready"
  fi
}

check_live_node_control_plane() {
  local node="$1"
  local should_have_role="$2"
  local has_role=false

  if kubectl_json get node "${node}" | jq -e \
    '.metadata.labels["node-role.kubernetes.io/control-plane"] != null' >/dev/null; then
    has_role=true
  fi

  if [[ "${has_role}" == "${should_have_role}" ]]; then
    note_ok "live node ${node} control-plane role is ${should_have_role}"
  else
    note_fail "live node ${node} control-plane role is ${has_role}, expected ${should_have_role}"
  fi
}

check_live_static_pod() {
  local component="$1"
  local node="$2"
  local pod="${component}-${node}"

  if kubectl -n kube-system get pod "${pod}" -o json | jq -e \
    '.status.phase == "Running" and ([.status.containerStatuses[]? | select(.ready == true)] | length) >= 1' >/dev/null; then
    note_ok "live ${pod} is running"
  else
    note_fail "live ${pod} is not running"
  fi
}

check_live_common() {
  need_cmd kubectl || true
  need_cmd jq || true

  for node in "${EXPECTED_NODES[@]}"; do
    check_live_node_ready "${node}"
  done

  if [[ "$(kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded -o json | jq '.items | length')" == "0" ]]; then
    note_ok "live cluster has no non-running pods"
  else
    note_fail "live cluster has non-running pods"
    kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide >&2 || true
  fi

  if kubectl get applications.argoproj.io -n argocd -o json >/tmp/soyspray-argo-apps.json 2>/dev/null &&
    jq -e 'all(.items[]; .status.sync.status == "Synced" and .status.health.status == "Healthy")' /tmp/soyspray-argo-apps.json >/dev/null; then
    note_ok "live Argo CD apps are Synced and Healthy"
  else
    note_fail "live Argo CD apps are not all Synced and Healthy"
    kubectl get applications.argoproj.io -n argocd \
      -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status --no-headers >&2 || true
  fi

  if kubectl -n longhorn-system get volumes.longhorn.io -o json >/tmp/soyspray-longhorn-volumes.json 2>/dev/null &&
    jq -e 'all(.items[]; .status.robustness == "healthy" and (.spec.numberOfReplicas | tonumber) >= 3)' /tmp/soyspray-longhorn-volumes.json >/dev/null; then
    note_ok "live Longhorn volumes are healthy with at least 3 replicas"
  else
    note_fail "live Longhorn volumes are not all healthy with at least 3 replicas"
    kubectl -n longhorn-system get volumes.longhorn.io \
      -o custom-columns=NAME:.metadata.name,STATE:.status.state,ROBUSTNESS:.status.robustness,REPLICAS:.spec.numberOfReplicas --no-headers >&2 || true
  fi
}

check_live_etcd() {
  local node="$1"
  local ip="${NODE_IPS[$node]}"
  local expected_members="$2"
  local output

  output="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "ubuntu@${ip}" \
    "sudo etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/ssl/etcd/ssl/ca.pem --cert=/etc/ssl/etcd/ssl/admin-${node}.pem --key=/etc/ssl/etcd/ssl/admin-${node}-key.pem member list -w json" 2>/dev/null)" || {
    note_fail "live etcd member list failed on ${node}"
    return
  }

  if jq -e --argjson expected "${expected_members}" '.members | length == $expected' <<<"${output}" >/dev/null; then
    note_ok "live etcd on ${node} sees ${expected_members} member(s)"
  else
    note_fail "live etcd on ${node} does not see ${expected_members} member(s)"
  fi

  if [[ "${expect}" == "ha" ]]; then
    if jq -e '[.members[].peerURLs[]] | sort == ["https://192.168.20.10:2380","https://192.168.20.11:2380","https://192.168.20.12:2380"]' <<<"${output}" >/dev/null; then
      note_ok "live etcd peer URLs are on 192.168.20.10-12"
    else
      note_fail "live etcd peer URLs are not the 192.168.20.10-12 set"
      jq -r '.members[].peerURLs[]' <<<"${output}" >&2 || true
    fi
  fi
}

check_live_current() {
  check_live_common

  for node in "${EXPECTED_NODES[@]}"; do
    if [[ "${node}" == "node-0" ]]; then
      check_live_node_control_plane "${node}" true
    else
      check_live_node_control_plane "${node}" false
    fi
  done

  for component in kube-apiserver kube-controller-manager kube-scheduler; do
    check_live_static_pod "${component}" node-0
  done

  check_live_etcd node-0 1

  if kubectl -n kube-system get deploy coredns -o json | jq -e '.status.availableReplicas >= 1' >/dev/null; then
    note_ok "live CoreDNS has at least 1 available replica"
  else
    note_fail "live CoreDNS has no available replicas"
  fi
}

check_live_ha() {
  check_live_common

  for node in "${EXPECTED_NODES[@]}"; do
    check_live_node_control_plane "${node}" true
    for component in kube-apiserver kube-controller-manager kube-scheduler; do
      check_live_static_pod "${component}" "${node}"
    done
    check_live_etcd "${node}" 3
  done

  if kubectl -n kube-system get pod -l k8s-app=kube-vip -o json | jq -e '.items | length == 3 and all(.[]; .status.phase == "Running")' >/dev/null; then
    note_ok "live kube-vip static pods are running on all control-plane nodes"
  else
    note_fail "live kube-vip static pods are not running on all control-plane nodes"
    kubectl -n kube-system get pod -l k8s-app=kube-vip -o wide >&2 || true
  fi

  if kubectl --server="https://${vip}:6443" --request-timeout=10s get --raw=/readyz >/dev/null; then
    note_ok "live API VIP ${vip}:6443 answers /readyz"
  else
    note_fail "live API VIP ${vip}:6443 does not answer /readyz"
  fi

  if kubectl -n kube-system get deploy coredns -o json | jq -e '.status.availableReplicas >= 2' >/dev/null; then
    note_ok "live CoreDNS has at least 2 available replicas"
  else
    note_fail "live CoreDNS has fewer than 2 available replicas"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --expect-current)
      expect="current"
      ;;
    --expect-ha)
      expect="ha"
      ;;
    --repo-only)
      repo_only=true
      ;;
    --live)
      live=true
      ;;
    --vip)
      shift
      vip="${1:?--vip requires an IP address}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "${repo_only}" == false && "${live}" == false ]]; then
  repo_only=true
fi

if [[ "${expect}" == "current" ]]; then
  check_repo_current
else
  check_repo_ha
fi

if [[ "${live}" == true ]]; then
  if [[ "${expect}" == "current" ]]; then
    check_live_current
  else
    check_live_ha
  fi
fi

if [[ "${failures}" -gt 0 ]]; then
  printf '\n%d check(s) failed\n' "${failures}" >&2
  exit 1
fi

printf '\nall requested HA stretch checks passed\n'
