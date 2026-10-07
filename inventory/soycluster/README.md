# Cluster inventory

The [upgrade readiness runbook](../../docs/upgrade-readiness.md) prepares the
next stock Kubespray tag, Kubernetes 1.36 prerequisites and Ubuntu 24.04
maintenance. It changes no running version.

Soyspray owns the three-node inventory and group variables here. The `kubespray`
submodule uses upstream `kubernetes-sigs/kubespray` v2.31.0 at
`1c9add48975060f45396b34d8e022c30d7f80dab`. Edit inventory and source pins through
a CI-green PR. `kubeadm_patches: []` disables patches; the unused local patch
files are retired. No upstream source patches are applied.

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
All Authentik API OIDC inputs live in `group_vars/k8s_cluster/k8s-cluster.yml`.
Inventory alone is the complete foundation input. `make setup` installs the
pinned upstream requirements (Ansible 11.13.0 at v2.31.0), plus repository tooling.

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
  --become --become-user=root --user ubuntu kubespray/cluster.yml
```

Follow the [pinned upstream upgrade guide](https://github.com/kubernetes-sigs/kubespray/blob/v2.31.0/docs/operations/upgrades.md):

1. Move one Kubespray tag at a time; never skip a minor release.
2. Read its release notes and diff our `group_vars` against that tag's `inventory/sample`.
3. Install that tag's `requirements.txt` (`make setup` also installs compatible repository tooling).
4. Set inventory `kube_version` within that tag's supported range.
5. Take an etcd snapshot and verify its private laptop copy after the native health gates.
6. Run full `kubespray/upgrade-cluster.yml` with the inventory alone, no extra-vars files, limits or tags.

A control-plane flag change also uses `upgrade-cluster.yml`; do not force restarts
with `upgrade_cluster_setup` on a normal `cluster.yml` run. Upstream's upgrade
playbook sets that internal flag itself. OIDC lives in inventory alongside the
other API settings, so a stock upstream invocation preserves authentication.

Run the native upgrade from delivered main after those gates:

```sh
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu kubespray/upgrade-cluster.yml
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


## Retired divergence

Node labels come from inventory `node_labels`. The stale top-level wrapper,
one-off etcd peer repair and imperative resource-limit patches are retired.
The pinned MetalLB template exposes no resource-limit variable; accept its
native defaults. Live inspection on 2026-10-07 found empty requests/limits for
MetalLB controller and speaker and the legacy ingress controller; after source
retirement the same UIDs and empty resources remain. No live foundation run or
limit patch was performed. The old patch targets no Argo-managed workload, so
there are no Argo values to migrate. The legacy ingress controller is outside
the current Argo catalog and pinned Kubespray source and needs a separately
reviewed replacement before the next Kubernetes upgrade.

Host utilities install only Python Kubernetes bindings, collectl, lshw, parted,
sysstat, smartmontools and jq. Tailscale and rsyslog have separate host purposes.
They neither write Kubespray configuration nor install/replace Kubernetes,
etcd, CNI, kube-vip or container runtime binaries. Package updates are scoped to
these names; no distro upgrade is performed by the utilities.
