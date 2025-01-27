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
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/prepare-longhorn-prereqs.yml
```

## ArgoCD does not uninstall LongHorn

remove LongHorn manually

Force delete stuck pods etc

```bash
for p in $(kubectl get pods -n longhorn-system -o name); do
    kubectl delete $p -n longhorn-system
done
```

Remove finalizers from pods

```bash
for p in $(kubectl get pods -n longhorn-system -o name); do
    kubectl patch $p -n longhorn-system --type=merge -p '{"metadata":{"finalizers":null}}'
done
```

```bash
for ds in $(kubectl get ds -n longhorn-system -o name); do
    kubectl delete $ds -n longhorn-system
done
```

```bash
for d in $(kubectl get deploy -n longhorn-system -o name); do
    kubectl delete $d -n longhorn-system
done
```

Force delete namespace

```bash
kubectl delete ns longhorn-system
```

Remove finalizers from the namespace

```bash
kubectl get namespace longhorn-system -o json > longhorn-system.json
jq 'del(.spec.finalizers)' longhorn-system.json > tmp.json && mv tmp.json longhorn-system.json
kubectl replace --raw "/api/v1/namespaces/longhorn-system/finalize" -f ./longhorn-system.json
rm ./longhorn-system.json
```

`longhorn-system` namespace gets stuck in a "Terminating" state.

Delete storage

```bash
kubectl delete sc longhorn longhorn-static
```

Delete CRDs

```bash
kubectl delete crd \
  backingimagedatasources.longhorn.io \
  backingimagemanagers.longhorn.io \
  backingimages.longhorn.io \
  backupbackingimages.longhorn.io \
  backups.longhorn.io \
  backuptargets.longhorn.io \
  backupvolumes.longhorn.io \
  engineimages.longhorn.io \
  engines.longhorn.io \
  instancemanagers.longhorn.io \
  nodes.longhorn.io \
  orphans.longhorn.io \
  recurringjobs.longhorn.io \
  replicas.longhorn.io \
  settings.longhorn.io \
  sharemanagers.longhorn.io \
  snapshots.longhorn.io \
  supportbundles.longhorn.io \
  systembackups.longhorn.io \
  systemrestores.longhorn.io \
  volumeattachments.longhorn.io \
  volumes.longhorn.io
```

Patch stuck CRDs

```bash
kubectl patch crd engineimages.longhorn.io engines.longhorn.io volumes.longhorn.io nodes.longhorn.io replicas.longhorn.io volumeattachments.longhorn.io backuptargets.longhorn.io \
  --type=merge -p '{"metadata":{"finalizers":[]}}'
```

Check no longhorn left

```bash
kubectl get ns longhorn-system
kubectl get crd | grep longhorn
kubectl get sc | grep longhorn
kubectl get pv -A | grep longhorn
```

## 1.8.0

longhorn-manager

```text
time="2025-01-24T22:13:13Z" level=fatal msg="Error starting manager: upgrade resources failed: upgrade from v1.7.x to v1.8.0: upgrade system backup failed: failed to get default backup target: backuptargets.longhorn.io \"default\" not found" func=main.main.DaemonCmd.func3 file="daemon.go:105"
```

## [text](https://longhorn.io/docs/1.8.0/deploy/uninstall/#uninstalling-longhorn-using-kubectl)

```sh
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.0/uninstall/uninstall.yaml
#job.batch/longhorn-uninstall created
```

retry

```sh
kubectl delete job longhorn-uninstall -n longhorn-system
```

stuck volume

```sh
kubectl get volumes.longhorn.io/pvc-cd72be8e-a730-4f27-8ba3-24fb2d2d9de9 -n longhorn-system -oyaml | \
  sed '/finalizers:/,/^  [^ ]/d' | \
  kubectl replace -f - --force --grace-period=0
```

 /var/lib/longhorn clean up

 ```sh
 ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/cleanup-longhorn.yml --extra-vars "skip_confirmation=true"
 ```
