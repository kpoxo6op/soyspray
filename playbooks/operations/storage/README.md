# Storage operations

Use these Ansible operations for deliberate changes to existing storage.
Keep Kubespray responsible for the cluster foundation and Longhorn
responsible for volume replicas.

## Protect Loki before node-2 removal

Loki currently has one replica on node-2. Run the reviewed native expansion
before disabling or evacuating node-2 storage:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/storage/protect-loki-before-node2.yml --check
```

After check mode passes, omit `--check`. The operation verifies the original
claim and volume identities, changes only `numberOfReplicas` from one to two,
and waits for one running copy on node-2 and one on a survivor. It is safe to
repeat. Do not start Longhorn eviction until this operation reports two healthy
replicas.

## Retained node-2 filesystem

`prepare-existing-longhorn-storage.yml` installs Longhorn host prerequisites
and mounts the existing node-2 filesystem by its verified UUID. It refuses a
changed node, address, filesystem type, or disk model. It never creates a
partition, filesystem, or label.

Run it in check mode before and after the retained-OS reset:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/storage/prepare-existing-longhorn-storage.yml --check
```

Omit `--check` only after the output identifies node-2, `192.168.20.12`, UUID
`49c092f4-dd55-41f5-99c6-854f8b44af4e`, ext4, and the PNY 500GB SATA disk.
This operation reuses the filesystem. Use neither storage initializer during
the node rebuild.

## Evacuate and restore node-2 replicas

`evacuate-node2.yml` records every live node-2 replica in private state,
disables target scheduling, temporarily uses the two survivor copies, requests
native Longhorn eviction, and waits for every affected volume to be healthy on
node-0 and node-1. It does not delete Replica objects or storage paths.

After the retained OS rejoins through Kubespray,
`restore-node2-replicas.yml` uses that private plan to re-enable scheduling and
restore every recorded replica policy. Loki returns to its original one-copy
monitoring policy; three-copy volumes rebuild on node-2. Use the exact commands
and ordering in `../nodes/README.md`.

Run restoration from exact current `main`. Keep the original evacuation file
unchanged if a recovery fix is merged between stages. Its recorded revision must
be an ancestor of the running revision; node, disk, and volume identities must
still match before any policy changes.

Longhorn can recreate its Node resource and disk map key during rejoin. The
restore matches `/storage` to its retained filesystem UUID and on-disk Longhorn
identity, then tests the current resource UID and spec before patching. A
pre-removal rollback still requires the original Node UID and disk key.
Restoration waits for every required engine copy to report synchronized `RW`.

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
