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
