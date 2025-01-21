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

## Storage Preparation

Before installing Longhorn, clean the SDA devices that were previously used by Ceph:

```bash
# Clean SDA devices on all nodes
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/clean-sda-devices.yml
```

Manually increased liveness probe timeout to see if it helps with csi plugin on
node-1

```text
kubectl -n longhorn-system patch daemonset longhorn-csi-plugin --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/2/livenessProbe/timeoutSeconds",
    "value": 15
  },
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/2/livenessProbe/periodSeconds",
    "value": 30
  },
  {
    "op": "replace",
    "path": "/spec/template/spec/containers/2/livenessProbe/failureThreshold",
    "value": 10
  }
]'
```

## Manual Cleanup

If the `longhorn-system` namespace gets stuck in a "Terminating" state:

Force Delete the Namespace

```bash
kubectl get namespace longhorn-system -o json > longhorn-system.json
```

Remove the `finalizers` field from the JSON file.

Apply the changes

```bash
kubectl replace --raw "/api/v1/namespaces/longhorn-system/finalize" -f ./longhorn-system.json
```

Delete storage classes

`kubectl delete  sc longhorn longhorn-static`

## Preflight checks

`longhornctl check preflight --kube-config ~/.kube/config`
