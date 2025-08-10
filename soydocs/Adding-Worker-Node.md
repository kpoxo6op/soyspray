# Adding Node-3 to Kubernetes Cluster

This document describes the process of adding a new worker node (node-3) to the existing Kubespray-based Kubernetes cluster.

## Prerequisites

- New mini PC with Ubuntu Server 24.04 installed
- Static IP configured: 192.168.50.103
- SSH access from management machine verified
- SSH keys properly configured

## Steps

### 1. Update Inventory

Added the new node to the Kubespray inventory file:

```yaml
# Added to kubespray/inventory/soycluster/hosts.yml
    node-3:
      ansible_host: 192.168.50.103
      ip: 192.168.50.103
      access_ip: 192.168.50.103

# Added to kube_node group
    kube_node:
      hosts:
        node-0:
        node-1:
        node-2:
        node-3:
```

### 2. Run Facts Playbook

This gathers information about all nodes in the cluster:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/playbooks/facts.yml
```

### 3. Scale the Cluster

Run the scale playbook to add the new node to the cluster:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu kubespray/scale.yml --limit=node-3
```

The `--limit=node-3` flag ensures operations are performed only on the new node without disturbing the existing cluster.

### 4. Verify Node

After scaling completes, verify the new node is properly joined. Initially, `node-3` had the role `<none>`.

```bash
kubectl get nodes
```

### 5. Ensure Node Labels

Run the custom `set-node-labels.yml` playbook to apply the correct `worker` role label. This playbook runs from the control plane and updates all nodes, so no `--limit` is needed.

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/set-node-labels.yml
```

After running, `kubectl get nodes` confirmed `node-3` has the `worker` role.

## Rebalancing the Cluster

After adding a new node, especially one with different hardware capabilities than existing nodes, it's important to rebalance workloads across the cluster. This ensures optimal resource utilization and performance.

### 1. Gather Hardware Information

First, collect hardware details of all nodes to understand their capabilities:

```bash
./hw.sh > hw-before.txt
```

In our case, this showed:

- Nodes 0-2: Intel Celeron N3350 (2 cores) with 5.6GB RAM
- Node-3: Intel Core i5-8500T (6 cores) with 7.1GB RAM

### 2. Run the Rebalance Playbook

To rebalance, we created a playbook that drains and uncordons nodes, allowing pods to be rescheduled on more appropriate nodes. Run this playbook for each node that should have its workloads redistributed:

```bash
# Rebalance first node
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu \
  playbooks/rebalance-cluster.yml -e "skip_confirmation=true" -e "delete_emptydir=true" \
  -e "single_node=node-1" -e "wait_time=240"

# Continue with other nodes as needed
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu \
  playbooks/rebalance-cluster.yml -e "skip_confirmation=true" -e "delete_emptydir=true" \
  -e "single_node=node-0" -e "wait_time=240"

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu \
  playbooks/rebalance-cluster.yml -e "skip_confirmation=true" -e "delete_emptydir=true" \
  -e "single_node=node-2" -e "wait_time=240"
```

Key parameters:

- `single_node`: Specifies which node to drain
- `delete_emptydir=true`: Required for pods using emptyDir volumes (like ArgoCD)
- `wait_time=240`: Allows 4 minutes for pods to reschedule
- `skip_confirmation=true`: Runs without interactive prompts

### 3. Verify Rebalancing

After running the playbook on each node, collect hardware information again to confirm the rebalancing:

```bash
./hw.sh > hw-after.txt
```

### 4. Results

Our rebalancing achieved:

| Node | CPU | Before | After | Change |
|------|-----|--------|-------|--------|
| node-0 | Celeron (2 cores) | ~10 pods | 6 pods | -4 |
| node-1 | Celeron (2 cores) | ~16 pods | 7 pods | -9 |
| node-2 | Celeron (2 cores) | ~12 pods | 7 pods | -5 |
| node-3 | i5 (6 cores) | ~7 pods | 28 pods | +21 |

The rebalancing moved most application workloads to the more powerful i5 node, while leaving only essential system components (DaemonSets, control plane components) on the Celeron nodes.

## References

- [Kubespray Adding/replacing a node documentation](kubespray/docs/operations/nodes.md)
- [Kubespray scale playbook](kubespray/playbooks/scale.yml)
