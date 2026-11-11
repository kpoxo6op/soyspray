# Storage operations

Use these operations for deliberate changes to existing storage. Kubespray
owns the cluster foundation. Longhorn owns replica placement and recovery.

## Voice model disk blocked by multipath

[`repair-voice-multipath.yml`](repair-voice-multipath.yml) repairs a
Speech-to-Phrase mount blocked by an unused multipath map. It resolves the
existing `home-automation/speech-to-phrase-data-v1` claim and its current node,
requires healthy Longhorn storage, verifies the iSCSI LUN and map identity,
and refuses a map with active users or additional disks. It excludes that
WWID in `/etc/multipath/conf.d/soyspray-voice.conf`, reloads multipath, and releases
only that unused map. Kubelet retries the mount without deleting a pod or PVC.
The WWID may be shared by Longhorn LUNs; the operation refuses an exclusion
that would also match non-Longhorn storage.

From the reviewed and pushed branch:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/storage/repair-voice-multipath.yml \
  -e voice_control_plane=node-0 --check
```

Remove `--check` to apply. The operation waits for Speech-to-Phrase readiness
and verifies that the PVC UID and volume name stayed the same. It does not
format, restore, detach, or back up data. A healthy volume is not evidence of
a completed backup. Run the voice transport checks and a spoken device test
after recovery. This does not configure multipath on other nodes.
The API reader must be a control-plane node with `python3-kubernetes` installed;
`voice_control_plane` selects it without changing the volume's actual node.

To undo the exclusion, remove only the managed fragment through Ansible and
run `multipathd reconfigure` on the same node. This may reintroduce the original
mount conflict. Preserve the voice claim and models during rollback.

The underlying conflict is described in the
[Longhorn troubleshooting guide](https://longhorn.io/kb/troubleshooting-volume-with-multipath/).

## Disposable monitoring replicas

[`monitoring-replicas.yml`](monitoring-replicas.yml) can reduce Prometheus and
Loki to one replica when scheduling capacity is needed for recovery. It keeps
claims, volume identities, storage classes, and workloads. It does not change
critical data, database, Redis, or media volumes.

Run it from the reviewed checkout:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
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

For single-node maintenance, retain three monitoring replicas with
`monitoring-replicas.yml -e monitoring_replicas=3`. First run
`reserve-replica-capacity.yml` with `--check`, then apply it from a pushed
revision. It changes only the known SSD reservations from 30% to 15%, with
identity and free-space guards; it leaves the stale node-0 disk entry untouched.
Wait for all attached volumes to be healthy and verify three running RW replicas
on distinct nodes before disconnecting hardware. The reservation does not change
100% provisioning or the 25% actual-free-space floor.

Both replica-capacity operations run on the laptop with its existing kubeconfig
and Kubernetes Python client in `soyspray-venv`; no extra Python packages are
installed on cluster nodes. Override `kubeconfig_path` for another private config.

## Longhorn mounts during failover

`repair-longhorn-multipath.yml` applies the same device/WWID, exclusive-slave and
zero-open-user guards to an explicitly named existing claim. Run from a pushed
revision with the three-node inventory and the laptop's Kubernetes environment:

```sh
ansible-playbook -i inventory/soycluster/hosts.yml --user ubuntu \
  playbooks/operations/storage/repair-longhorn-multipath.yml \
  -e storage_namespace=postgresql -e storage_claim=immich-db-a-3 --check
```

Remove `--check` only after the guard identifies the intended unused map. It
writes `soyspray-longhorn.conf` on the claim's current node and releases only
that map. With no map, it still installs the exclusion to prevent the conflict
on later attaches. It refuses a shared WWID used by any non-Longhorn device.
It does not format devices, delete pods/claims, or detach volumes. Verify the
original claim identity and the consuming application's readiness afterwards.
The selected volume must be attached and healthy. Restore the previous fragment
through Ansible and reconfigure multipath to roll back, acknowledging that this
can bring the mount conflict back. Do not flush maps globally.
