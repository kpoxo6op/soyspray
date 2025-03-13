# Longhorn Maintenance Procedures

This document contains maintenance procedures for Longhorn, particularly focused on cleanup and deletion when standard processes fail.

## Uninstalling Longhorn

ArgoCD may not properly uninstall Longhorn. If you need to manually remove Longhorn, follow these steps.

### Force Delete Stuck Pods

```bash
for p in $(kubectl get pods -n longhorn-system -o name); do
    kubectl delete $p -n longhorn-system
done
```

### Remove Finalizers from Pods

```bash
for p in $(kubectl get pods -n longhorn-system -o name); do
    kubectl patch $p -n longhorn-system --type=merge -p '{"metadata":{"finalizers":null}}'
done
```

### Delete DaemonSets and Deployments

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

### Force Delete Namespace

```bash
kubectl delete ns longhorn-system
```

### Remove Finalizers from the Namespace

If the `longhorn-system` namespace gets stuck in a "Terminating" state:

```bash
kubectl get namespace longhorn-system -o json > longhorn-system.json
jq 'del(.spec.finalizers)' longhorn-system.json > tmp.json && mv tmp.json longhorn-system.json
kubectl replace --raw "/api/v1/namespaces/longhorn-system/finalize" -f ./longhorn-system.json
rm ./longhorn-system.json
```

### Delete Storage Classes

```bash
kubectl delete sc longhorn longhorn-static
```

### Delete CRDs

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

### Patch Stuck CRDs

```bash
kubectl patch crd engineimages.longhorn.io engines.longhorn.io volumes.longhorn.io nodes.longhorn.io replicas.longhorn.io volumeattachments.longhorn.io backuptargets.longhorn.io \
  --type=merge -p '{"metadata":{"finalizers":[]}}'
```

### Check for Remaining Longhorn Resources

```bash
kubectl get ns longhorn-system
kubectl get crd | grep longhorn
kubectl get sc | grep longhorn
kubectl get pv -A | grep longhorn
```

### Using the Official Uninstaller

For a more automated approach, you can use Longhorn's official uninstaller:

```sh
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.0/uninstall/uninstall.yaml
# Creates: job.batch/longhorn-uninstall
```

If the uninstall job gets stuck, you can delete and retry:

```sh
kubectl delete job longhorn-uninstall -n longhorn-system
```

### Unstuck Volumes

If you have volumes that won't delete:

```sh
kubectl get volumes.longhorn.io/pvc-cd72be8e-a730-4f27-8ba3-24fb2d2d9de9 -n longhorn-system -oyaml | \
  sed '/finalizers:/,/^  [^ ]/d' | \
  kubectl replace -f - --force --grace-period=0
```

### Node Cleanup

To clean up Longhorn data from nodes:

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/cleanup-longhorn.yml --extra-vars "skip_confirmation=true"
```

## Version-Specific Issues

### Longhorn 1.8.0 Upgrade Notes

When upgrading to 1.8.0, you might encounter this error with longhorn-manager:

```text
time="2025-01-24T22:13:13Z" level=fatal msg="Error starting manager: upgrade resources failed: upgrade from v1.7.x to v1.8.0: upgrade system backup failed: failed to get default backup target: backuptargets.longhorn.io \"default\" not found" func=main.main.DaemonCmd.func3 file="daemon.go:105"
```

#### Official Uninstaller Reference

For reference, see the [official Longhorn uninstallation documentation](https://longhorn.io/docs/1.8.0/deploy/uninstall/#uninstalling-longhorn-using-kubectl).
