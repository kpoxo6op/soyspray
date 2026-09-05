# Storage operations

Use these Ansible operations for deliberate changes to existing storage.
Keep Kubespray responsible for the cluster foundation and Longhorn
responsible for volume replicas.

## Disposable monitoring data

`monitoring-replicas.yml` sets one Longhorn replica for the existing Prometheus
and Loki claims. Their metrics and logs can be collected again after a loss.
This frees reserved scheduling capacity for restores and durable data. The
operation keeps the claims, volume identities, storage classes, and running
workloads. It does not change critical data, database, Redis, or media volumes.

The operation requires both claims to be bound and their volumes to be
healthy and attached. It checks the claim identity and rejects a volume in
the critical backup group. Each update tests the observed UID and complete
volume spec before changing only the replica count.

Push the branch and run `make go`. Check the change, then omit `--check` to
apply it:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/storage/monitoring-replicas.yml --check
```

Repeat the operation to verify that it makes no further changes. Check the
two Longhorn volumes and replica resources, their claims, and the Prometheus
and Loki readiness endpoints. Confirm that critical volumes still have three
replicas. The shared `longhorn` storage class stays unchanged; rerun this
operation if a deliberate rebuild creates new monitoring volumes.

For rollback, first ensure there is enough scheduling capacity, then run the
same operation with `-e monitoring_replicas=3`. Wait for replica rebuilds to
finish. One replica does not provide protection from the loss of its disk;
this policy is limited to disposable metrics and logs.
