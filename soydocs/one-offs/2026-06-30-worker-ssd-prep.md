# 2026-06-30 Worker SSD And RAM Prep

## Context

Two PNY CS900 500GB SATA SSDs are expected for `node-1` and `node-2`.
Prepare them as Longhorn data disks after they are physically installed.

Two RAM kits are also ordered for `node-1` and `node-2` so the worker nodes can
be brought closer to the `node-0` memory profile.

## Parked Handoff Before Install

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

## Provisioning Result On 2026-07-01

The worker SSDs were installed, prepared with
`playbooks/operations/storage/prepare-longhorn-worker-ssd.yml`, and mounted at
`/storage`.

| Node | SSD by-id path | Filesystem UUID | Longhorn disk UUID |
| --- | --- | --- | --- |
| `node-1` | `/dev/disk/by-id/ata-PNY_500GB_SATA_SSD_PNL03260552550304519` | `47a1ece0-aca9-4f1d-8ac1-b3a1ee9c699a` | `96833268-f6cb-4dd8-b52c-27e0777b1a02` |
| `node-2` | `/dev/disk/by-id/ata-PNY_500GB_SATA_SSD_PNL03260552550303454` | `49c092f4-dd55-41f5-99c6-854f8b44af4e` | `062dcb89-f3cf-4eb3-af9d-683c0372e83a` |

Final host state:

- `node-1`: `/dev/sda1` mounted at `/storage`, ext4, 458G size, 435G
  available.
- `node-2`: `/dev/sda1` mounted at `/storage`, ext4, 458G size, 435G
  available.
- Both mounts are persisted in `/etc/fstab` by filesystem UUID with
  `defaults,noatime,nofail,x-systemd.device-timeout=10s`.
- A write/sync/delete test succeeded on `/storage` on both workers.

Longhorn reconciliation:

- The old root-backed worker disk entries reported `DiskFilesystemChanged`
  after the SSDs were mounted.
- There were zero Longhorn replicas on `node-1` or `node-2`, so the stale empty
  disk entries were disabled, removed, and re-added against the new SSD-backed
  `/storage` filesystems.
- `node-1` and `node-2` now report Longhorn disk `Ready=True` and
  `Schedulable=True`.
- `storageReserved` is `147331952640` bytes on each worker, matching the
  reservation size used for the 500GB PNY disk on `node-0`.

Replica expansion:

- Longhorn defaults were moved to three replicas for new default-class volumes.
- All 20 active Longhorn workload volumes were patched to
  `numberOfReplicas=3`.
- Longhorn rebuilt the new replicas across `node-0`, `node-1`, and `node-2`.
- Final check at `2026-07-01T15:15:21+12:00`: `20` active 3-replica volumes
  were `healthy`, engine modes were `RW:60`, and failed replicas remained `0`.
- One old preserved volume, `pvc-87a2e7b1-6011-4580-8dce-e9433a6f0900`,
  remains `unknown` with `numberOfReplicas=1`; it was not part of the active
  workload expansion.
- Final Longhorn disk schedule was balanced at roughly `303Gi` scheduled on
  each SSD-backed `/storage` disk, with all three disks reporting
  `Ready=True` and `Schedulable=True`.

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
      "node-1": "/dev/disk/by-id/ata-PNY_500GB_SATA_SSD_PNL03260552550304519",
      "node-2": "/dev/disk/by-id/ata-PNY_500GB_SATA_SSD_PNL03260552550303454"
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

## RAM Order And Install Prep

Boris placed the worker RAM order on 2026-06-30:

| Field | Value |
| --- | --- |
| AliExpress order | `8212777184122085` |
| Status when recorded | Processing |
| Store | StoreSkill Franchise Store |
| Item | `2PCS PUSKILL Killblade DDR4 Notebook Ram 32GB 16GB 8GB 1.2V 3200MHz 2666MHz 2400MHz 260-PiN Sodimm Memory` |
| Variant | `China Mainland`, `DDR4 16GB 2666x2pcs` |
| Quantity | `2` kits |
| Intended install | one `2x16GB` DDR4 SODIMM kit per worker node |
| Subtotal | `NZ$446.62` |
| Total paid | `NZ$513.61` |
| Estimated delivery | 2026-07-16 |

Do not assume the RAM has been installed just because the order exists. After
physical install, verify both workers live:

```sh
for host in 192.168.20.11 192.168.20.12; do
  ssh ubuntu@"$host" '
    hostname
    free -h
    sudo dmidecode -t memory | grep -E "Locator:|Size:|Speed:|Part Number:" | sed "s/^/  /"
  '
done
```

Expected target state after install:

- `node-1`: roughly 32 GiB RAM from two 16 GB DDR4 SODIMMs.
- `node-2`: roughly 32 GiB RAM from two 16 GB DDR4 SODIMMs.
- `node-0`: remains the larger baseline node with its existing 32 GB plus 4 GB
  layout unless it is changed separately.

If the RAM upgrade changes scheduling assumptions, capture the new live output
in this note and then decide whether any workload placement, requests, or
Kong/lab sizing docs need to be adjusted.

## Remaining Follow-Up

The SSD install and Longhorn disk reconciliation are complete. Remaining work:

- Add the new worker SSD by-id paths to
  `playbooks/argocd/applications/observability/prometheus/smartctl-exporter-daemonset.yaml`
  if the exporter can tolerate per-node missing devices, or split the exporter
  into node-specific device args.
- Reconcile GitOps drift by merging the branch containing the Longhorn
  three-replica defaults and then syncing the Longhorn Argo app back to `HEAD`.
