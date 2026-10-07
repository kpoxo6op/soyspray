# Cluster inventory

Soyspray owns the three-node inventory and group variables here. The `kubespray`
submodule uses upstream `kubernetes-sigs/kubespray` v2.31.0 at
`1c9add48975060f45396b34d8e022c30d7f80dab`. Edit inventory and source pins through
a CI-green PR. The `patches/` files are kubeadm configuration inputs, not
Kubespray source patches; the active inline `kubeadm_patches` list is preserved.

Argo owns cert-manager controllers and CRDs at v1.17.1. Keep
`cert_manager_enabled: false`: the upstream addon deletes its namespace.
[Cert-manager checks](../../apps/cert-manager/README.md) cover admission,
certificate readiness, CA injection and ingress TLS.

```sh
source soyspray-venv/bin/activate
ansible-inventory -i inventory/soycluster/hosts.yml --graph
make check
```

Keep `credentials/` private and untracked. Preserve the existing
`kubeadm_certificate_key.creds`; the credentials directory can point to its
original private location. Never generate a replacement during reconciliation.
The existing Authentik variable file preserves live API OIDC authentication;
pass it to every full cluster or upgrade run.

## Application foundation ownership

Argo owns cert-manager and its own v2.14.5 runtime. Keep both
`cert_manager_enabled: false` and `argocd_enabled: false`: Kubespray must not
reconcile either installation. Argo controller settings and private inputs stay
with Ansible. See [Argo runtime ownership](../../apps/argocd/README.md).

The admin credential belongs to its private recovery Vault and guarded Ansible
operation. Normal Authentik bootstrap never rewrites it. Keep the valid UTC
session cutoff and preserve signing, OIDC and TLS keys; never restore an exposed
credential or re-enable the Kubespray addon. Full foundation runs use the normal
snapshot/health gates below. Inventory checks and native Ansible conditional
evaluation protect the disabled addons without repeating a live full run.

## Reconcile or upgrade

Use merged `main` and the complete inventory. Require three Ready nodes,
healthy three-member etcd, Synced/Healthy Applications and healthy attached
Longhorn volumes. Preserve the intentionally retained detached Jellyfin config
volume unchanged; its unknown robustness is expected. Take
`playbooks/operations/nodes/snapshot-etcd.yml` with an explicit timestamp/SHA
label, and verify the populated laptop copy before proceeding. See the
[node operations guide](../../playbooks/operations/nodes/README.md).

```sh
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu kubespray/cluster.yml \
  -e @playbooks/operations/security/kubernetes-authentik-oidc-vars.yml
```

For an upgrade, bump the upstream tag through a CI-green PR, repeat those gates
and snapshot, then run the native upgrade with the same inputs:

```sh
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu kubespray/upgrade-cluster.yml \
  -e @playbooks/operations/security/kubernetes-authentik-oidc-vars.yml
```

Use no node limit or tags for these full runs. Verify versions, API VIP
`192.168.20.13:6443`, SANs, etcd, Argo, storage and alerts afterwards. Verify the
cert-manager namespace UID and Ready Certificates. Stop and inspect any failed
run; never improvise a reset, removal or volume deletion.

## Accepted upstream behavior and rollback

The DNS autoscaler keeps the existing `kube-system/dns-autoscaler` ConfigMap.
Upstream does not reconcile the fork's template; future changes to that
ConfigMap need an explicit reviewed operation. The pinned kube-vip template
omits `hostPath.type` (the former fork used `FileOrCreate`); `admin.conf` exists
on every current node, and its pod may restart once. Drill,
check-mode, containerd-placeholder and stale-proxy cleanup patches are dropped.

The fork repository remains untouched as rollback source:
`https://github.com/kpoxo6op/kubespray` at
`53310f52940bea26962d403febcd6f9ac1f20dbf`. Roll back only the submodule URL/pin
through a CI-green PR, retaining this inventory, private credentials and
`cert_manager_enabled: false`. Cert-manager stays under Argo. A source revert
alone does not rerun the foundation; inspect live state before any deliberate
reconciliation. Preserve memberships, SANs, application data and device identity.
