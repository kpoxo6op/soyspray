# Kubespray Changes

This repo keeps Kubespray as a submodule because the cluster bootstrap and node-level
add-ons are managed by Kubespray, not by Argo CD.

Argo reconciles workloads under `playbooks/argocd/applications`, but it does not apply
Kubespray inventory or role changes. When a change affects Kubespray-managed resources,
the fix must land in the `kubespray` submodule, the parent `soyspray` repo must point at
that submodule commit, and a Kubespray playbook must be run against the cluster.

## NodeLocalDNS Upstreams

The 2026-06-01 DNS alert fix touched Kubespray because NodeLocalDNS is rendered from the
Kubespray inventory. The live problem was that NodeLocalDNS forwarded the root DNS zone
`.` to `/etc/resolv.conf`, which on this node fed back into cluster/local DNS behavior and
caused noisy NodeLocalDNS error bursts.

The intended cluster behavior is:

- `lan` and `soyspray.vip` forward to the OpenWrt router at `192.168.20.1`
- the default root zone `.` forwards to explicit public upstreams, currently `1.1.1.1`
  and `9.9.9.9`
- cluster zones continue to forward to CoreDNS

After merging a parent repo PR that updates the Kubespray submodule pointer, apply the
Kubespray-managed resource explicitly:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  kubespray/cluster.yml --tags nodelocaldns
```

Verify the live Corefile:

```sh
kubectl -n kube-system get cm nodelocaldns -o jsonpath='{.data.Corefile}'
kubectl -n kube-system rollout status ds/nodelocaldns --timeout=120s
```

## Historical Upgrade Note

For a full Kubespray version upgrade, check out the desired Kubespray tag or branch in
the submodule, reapply local inventory customizations, update `kube_version`, and run the
upgrade playbook:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  kubespray/upgrade-cluster.yml
```
