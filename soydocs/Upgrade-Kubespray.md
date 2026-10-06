# Kubespray changes and upgrades

Soyspray owns `inventory/soycluster/`; Kubespray is pinned separately under
`kubespray/`. Inventory changes land in a Soyspray pull request. Argo CD does
not reconcile the cluster foundation. Use the native node README before any
Ansible operation that changes the foundation.

The current fork pin is unchanged. Switching to upstream v2.31.0 is blocked:
its enabled cert-manager addon deletes the configured namespace during
reconciliation, whereas the fork preserves it. The fork also reconciles the
DNS autoscaler ConfigMap explicitly. No inventory variable reproduces the
namespace protection. Do not run upstream against the live cluster until
static parity and ownership safety are established.

A detached Longhorn volume with unknown robustness also fails the strict
all-volumes-healthy reconciliation gate. Keep data and credentials intact;
do not delete or force repair a volume to make a gate pass.

## DNS settings

The inventory keeps NodeLocalDNS forwarding for `lan` and `soyspray.vip` to
OpenWrt at `192.168.20.1`, and explicit root upstreams `1.1.1.1` and `9.9.9.9`.
The path move changes none of these settings.

## Future upgrade

A version upgrade is a separate reviewed tag bump. Before running, require
three Ready nodes, healthy three-member etcd, healthy Argo Applications and
Longhorn volumes, plus a verified off-node etcd snapshot. Use the complete
inventory with the native upgrade entrypoint:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  kubespray/upgrade-cluster.yml
```

The current inventory move performs no upgrade or live foundation run.
See [the node guide](../playbooks/operations/nodes/README.md) for snapshot,
health, source, and rollback conventions.
