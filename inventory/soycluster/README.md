# Cluster inventory

Soyspray owns the three-node inventory and group variables here. Kubespray stays
pinned separately under `kubespray/`; the fork repository is unchanged. Edit
`hosts.yml` and `group_vars/` through a CI-checked pull request. Read
`playbooks/operations/nodes/README.md` before any deliberate node operation.
The `patches/` files are kubeadm configuration inputs, not patches to Kubespray
source. The active inline `kubeadm_patches` list is unchanged.

```sh
source soyspray-venv/bin/activate
ansible-inventory -i inventory/soycluster/hosts.yml --graph
make check
```

Keep `credentials/` private and untracked. Preserve the existing
`kubeadm_certificate_key.creds`; the local credentials directory can point to
its original private location. Never generate a replacement as part of this
path migration. Use the standard `--become --become-user=root --user ubuntu`
options for node operations.

This move changes no versions, memberships, VIPs, SANs, app data, or live owners.
The upstream v2.31.0 migration is blocked: its enabled cert-manager addon deletes
the configured namespace during reconciliation, and its DNS autoscaler omits the
fork's explicitly reconciled ConfigMap. Do not run upstream against this cluster
until those effects have a native, safe equivalent and static parity is proved.
The fork and its old inventory remain the rollback reference.

For a future upgrade, change the upstream tag in a separate reviewed PR and use
full `upgrade-cluster.yml` after the native snapshot and health gates. This path
move does not perform or authorize that upgrade.

Rollback is a Git revert to the old inventory paths and the same provisioner
pin. Keep both private credential paths available; do not delete claims,
volumes, namespaces, or credentials during rollback.
