# Workload Placement Stretch

Date: 2026-07-01

This note follows the worker SSD install. Longhorn data replicas are already
spread across the three SSD-backed nodes. The next useful stretch is workload
placement: make safe Longhorn-backed singletons prefer the worker nodes, while
leaving node-local workloads obvious.

## Current Shape

```text
Longhorn data:

  node-0 SSD  +  node-1 SSD  +  node-2 SSD
       \            |             /
        \------ 3 replicas -------/

Not 3-node portable:

  media/media-downloads
    local PV: /srv/media/downloads
    node: node-0
    size: 1800Gi

  zigbee2mqtt
    uses host /dev for the USB coordinator
    node: node-0 until the device is moved and tested
```

## Changes In This Branch

- Add Kubespray-managed labels for the three SSD-backed Longhorn nodes.
- Mark `node-0` as the only node with the local media download disk.
- Set `longhorn-rwx` to create future RWX volumes with three replicas.
- Make small Longhorn-only services prefer `node-1` and `node-2`:
  - `media/prowlarr`
  - `media/threadfin`
  - `home-automation/mosquitto`
- Pin `zigbee2mqtt` to `node-0` because it uses host `/dev`.

These placement rules are intentionally soft for Longhorn-backed apps. If the
worker nodes are not available, the scheduler can still place them on `node-0`.

## Apply Order

Kubespray inventory labels do not apply through Argo CD. Apply them before
deploying the Argo app changes:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  kubespray/cluster.yml --tags node-label
```

Then deploy the Argo-managed apps:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml --tags longhorn,prowlarr,threadfin,mosquitto,zigbee2mqtt
```

## Expected Result

```text
node-0:
  control plane
  local media download disk
  zigbee USB workload
  can still run fallback Longhorn-backed apps

node-1 / node-2:
  preferred home for selected Longhorn-backed singleton apps
  Longhorn replicas already present
```

## Verification

```bash
kubectl get nodes --show-labels
kubectl get pods -n media -o wide | grep -E 'prowlarr|threadfin'
kubectl get pods -n home-automation -o wide | grep -E 'mosquitto|zigbee2mqtt'
kubectl get sc longhorn-rwx -o jsonpath='{.parameters.numberOfReplicas}{"\n"}'
```
