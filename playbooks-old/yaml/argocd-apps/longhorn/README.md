# Longhorn Storage

Distributed block storage system for Kubernetes. This setup is optimized for a resource-constrained
cluster, using minimal replicas and conservative resource limits.

## Configuration

- Using single replica to conserve resources
- Conservative CPU/memory limits
- Using sda devices on each node
- Default storage class enabled

## Hardware Configuration

Using the same devices as attempted with Rook/Ceph:

- node-0: /dev/sda
- node-1: /dev/sda
- node-2: /dev/sda

## Resource Usage

Much lighter than Ceph, configured with:

- Manager: 250m CPU, 256Mi memory
- Driver: 250m CPU, 256Mi memory
- Instance Manager: 250m CPU, 256Mi memory

Total per node: ~750m CPU, 768Mi memory

## Storage and Node Preparation

Created from longhornctl output

`longhornctl check preflight --kube-config ~/.kube/config`

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/initialize-longhorn-storage.yml
```

## Maintenance and Troubleshooting

For maintenance procedures, including uninstallation and cleanup, see:

- [Longhorn Maintenance Procedures](docs/README.md)

## Prometheus Storage Plan

We will create a high-performance storage solution for Prometheus using Longhorn on miniPC SSDs:

1. Create a dedicated `longhorn-monitoring` StorageClass with optimized settings
2. Configure single-replica volumes backed by the fastest SSD on each node
3. Configure Prometheus to use this storage via PersistentVolumeClaims
4. Implement proper retention and compaction settings

For detailed implementation plans, performance benchmarks, and configuration parameters, see:

- [Prometheus Storage Implementation Plan](docs/prometheus-storage.md)
