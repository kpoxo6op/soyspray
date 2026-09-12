# Storage operations

Use these operations for deliberate changes to existing storage. Kubespray
owns the cluster foundation. Longhorn owns replica placement and recovery.

## Disposable monitoring replicas

[`monitoring-replicas.yml`](monitoring-replicas.yml) can reduce Prometheus and
Loki to one replica when scheduling capacity is needed for recovery. It keeps
claims, volume identities, storage classes, and workloads. It does not change
critical data, database, Redis, or media volumes.

Run it from the reviewed checkout:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/storage/monitoring-replicas.yml --check
```

Apply only after the check identifies the intended claims and volumes. Wait
for the operation's health checks. For rollback, use the same operation with
`-e monitoring_replicas=3` and wait for replica rebuilds.

One replica is not protection from disk loss. This policy is limited to
disposable metrics and logs. Backups, isolated restores, and the node recovery
guide remain the supported recovery evidence; there is no separate node
evacuation or restore workflow.
