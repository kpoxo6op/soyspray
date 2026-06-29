# 2026-06-30 Worker SSD Prep

## Context

Two PNY CS900 500GB SATA SSDs are expected for `node-1` and `node-2`.
Prepare them as Longhorn data disks after they are physically installed.

## Parked Handoff For Next Session

Work is parked before the physical SSD installation boundary. In the next
session, assume Boris may have installed the new SSDs in `node-1` and `node-2`,
but verify the live device state before formatting anything.

Start here:

1. Run the discovery commands below and capture the stable `ata-PNY_...` by-id
   path for each worker.
2. Run `prepare-longhorn-worker-ssd.yml` with the discovered by-id paths to
   format, mount, and persist `/storage` on both workers.
3. Verify Longhorn node disk state before scheduling replicas to the workers.
4. Stretch the cluster deliberately: enable real worker-backed Longhorn storage,
   then decide which PVCs can move from one replica to two or three replicas.
5. Update monitoring once SSD serials are known: fix `smartctl-exporter` device
   args or split it into node-specific exporters, then verify SMART metrics for
   all three nodes.

Current live state checked on 2026-06-29:

| Node | Current storage state |
| --- | --- |
| `node-0` | Existing PNY 500GB SATA SSD at `/dev/sda1`, mounted at `/storage` |
| `node-1` | Only NVMe root disk present; `/storage` exists but is not a mountpoint |
| `node-2` | Only NVMe root disk present; `/storage` exists but is not a mountpoint |

Longhorn has already created `/storage` disk entries for the new workers while
`/storage` is still on the root filesystem. Do not schedule real data there
until the new SSDs are mounted and Longhorn disk state has been reconciled.

## Discover New SSD IDs

After installing the drives, collect stable device paths:

```sh
for host in 192.168.20.11 192.168.20.12; do
  ssh ubuntu@"$host" '
    hostname
    lsblk -e7 -o NAME,PATH,MODEL,SERIAL,SIZE,TYPE,FSTYPE,MOUNTPOINTS,TRAN,ROTA
    echo "--- by-id PNY links ---"
    find /dev/disk/by-id -maxdepth 1 -type l -printf "%f -> %l\n" | sort | grep -E "PNY|500GB|wwn" || true
    echo "--- /storage ---"
    mountpoint /storage || true
    df -hT / /storage 2>/dev/null || true
  '
done
```

Use the `ata-PNY_...` by-id link for each new whole disk. Do not use `/dev/sdX`
because those names can move.

## Prepare The Disks

Fill in the two by-id paths from the discovery output and run from the repo
root:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/storage/prepare-longhorn-worker-ssd.yml \
  -e longhorn_storage_force_format=true \
  -e '{
    "longhorn_storage_device_by_host": {
      "node-1": "/dev/disk/by-id/ata-PNY_500GB_SATA_SSD_REPLACE_NODE1_SERIAL",
      "node-2": "/dev/disk/by-id/ata-PNY_500GB_SATA_SSD_REPLACE_NODE2_SERIAL"
    }
  }'
```

The playbook refuses to run unless:

- A by-id path is provided per target host.
- The target resolves to a whole disk.
- The disk model contains `PNY` and `500GB`.
- The disk transport is `sata`.
- `/storage` is not already a mountpoint.
- The disk has no mounted children.
- `longhorn_storage_force_format=true` is explicitly passed.

## Post-Mount Checks

After the playbook completes:

```sh
for host in 192.168.20.11 192.168.20.12; do
  ssh ubuntu@"$host" '
    hostname
    mountpoint /storage
    df -hT /storage
    lsblk -e7 -o NAME,PATH,MODEL,SERIAL,SIZE,TYPE,FSTYPE,MOUNTPOINTS,TRAN,ROTA
  '
done
```

Then verify Longhorn before letting workloads rely on the new disks:

```sh
kubectl -n longhorn-system get nodes.longhorn.io node-1 node-2 -o yaml
kubectl -n longhorn-system get replicas.longhorn.io -o wide
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

If Longhorn reports the original root-backed `/storage` disk as not ready after
the mount, reconcile the Longhorn node disk entries before scheduling replicas
to the workers. Current `node-0` history shows the pattern: a stale default disk
can remain while a replacement `/storage` disk is active.

## Monitoring Prep

Grafana's Kubernetes and Longhorn dashboards do not need fixed-node changes for
the worker additions. They use Kubernetes/Longhorn metrics and should discover
the new nodes from Prometheus labels.

Live check on 2026-06-29 showed:

- `kube_node_info` count is `3`.
- `node-exporter` has three healthy targets:
  `192.168.20.10:9100`, `192.168.20.11:9100`, `192.168.20.12:9100`.
- `smartctl-exporter` is running on all three nodes, but SMART status metrics
  are currently emitted only by the original node-0 pod because the exporter
  args still point at node-0 by-id devices.

The `node-hardware` dashboard source was adjusted so disk throughput/utilization
series include `instance` as well as `device`. Without that, same-name devices
such as `nvme0n1` on different nodes get aggregated into one line.

## Follow-Up Repo Changes After Install

Once the two new serials are known:

- Add the new worker SSD by-id paths to
  `playbooks/argocd/applications/observability/prometheus/smartctl-exporter-daemonset.yaml`
  if the exporter can tolerate per-node missing devices, or split the exporter
  into node-specific device args.
- Record the final by-id paths and UUIDs in this runbook.
- Decide whether to keep Longhorn at one replica or move selected PVCs to two
  or three replicas after the workers have real SSD-backed `/storage`.
