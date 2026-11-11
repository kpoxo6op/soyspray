# Longhorn Storage

Distributed block storage system for Kubernetes. This setup is optimized for a
resource-constrained cluster with three SSD-backed storage nodes and
conservative resource limits.

## Configuration

- New default StorageClass volumes use three replicas across the SSD-backed
  storage nodes
- Conservative CPU/memory limits
- Using sda devices on each node
- Default storage class enabled

## Hardware Configuration

Devices:

- node-0: /dev/sda
- node-1: /dev/sda
- node-2: /dev/sda

## Resource Usage

Component CPU and memory requests and limits are set in
[`manifests/kustomization.yaml`](manifests/kustomization.yaml).

## Storage and Node Preparation

Created from longhornctl output

`longhornctl check preflight --kube-config ~/.kube/config`

The worker SSD preparation playbook is
`playbooks/operations/storage/prepare-longhorn-worker-ssd.yml`. It takes a
stable `/dev/disk/by-id` path per host.

## Observe storage and backup state

The upstream chart enables a ServiceMonitor labelled for the existing Prometheus
stack. It scrapes Longhorn managers every 60 seconds. This provides storage,
replica, backup-state and backup-size metrics without another exporter. The native
backup metrics do not include the snapshot time, so they do not prove backup age.
Use Longhorn Backup custom resources and the Longhorn UI for snapshot times.
The kube-state-metrics rules retain the native critical-backup age alerts.

Run `make check`, merge the pull request, and let Argo reconcile `main`. Verify the Application,
ServiceMonitor, Prometheus target health, and existing volume identities and
replica counts. Disabling the ServiceMonitor stops telemetry; it does not stop
Longhorn or change storage.

## Single-node outages

CSI controllers run three copies. Longhorn deletes terminating Deployment and
StatefulSet pods on a down node so their existing volumes can attach elsewhere.
This permits automatic recovery after Kubernetes marks and evicts the lost pods;
it is not uninterrupted service. Physically power off a node before disconnecting
its network for maintenance: a partitioned, still-running writer is not a safely
fenced machine. Never lose a second node until replicas have recovered.

The guarded `playbooks/operations/storage/reserve-replica-capacity.yml` operation
changes only the three known dedicated SSD reservations from 30% to 15%.
It requires matching disk identities, sizes, ready state and over 50% real free
space. The 100% provisioning limit and 25% minimum-free-space protection remain.
This makes room for the third Immich library copy, three monitoring copies and
additional PostgreSQL standbys. It neither formats disks nor moves mounts.
Restore the old reservation only after allocated replicas fit that smaller budget;
do not remove data or replicas merely to roll back the reservation.
