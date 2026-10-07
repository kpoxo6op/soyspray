# Security Operations

Cluster security playbooks for maintenance tasks.

- `sync-certificates.yml` - Synchronize TLS certificates across namespaces

## Argo access operations

Use the isolated checkout at delivered `main`, its Ansible environment and
the current kubeconfig. These operations refuse unmerged live execution.
The server Ingress sends HTTPS to the existing TLS-enabled Argo server;
`repair-argocd-ingress.yml` changes only its backend protocol and port, with
atomic UID/resourceVersion tests. It refuses a route outside the reviewed shape.

`rotate-argocd-admin.yml` reads the private encrypted recovery Vault, requires
a cutoff less than two minutes old and atomically tests the Secret's reviewed
UID/resourceVersion before replacing only the two admin fields. All credential
tasks suppress output. Keep a new 0600 pre-change copy under the private plans
directory. Never restore an old exposed credential. Unexpected non-admin
changes trigger an identity/version guarded recovery of only those keys, then
stop the operation. Keep kubectl available as break-glass.

Create or regenerate the private Vault locally with a long random password,
a cost-12 bcrypt hash and a current RFC3339 UTC `password_mtime`, under
`argocd_admin`. Encrypt it with the existing recovery vault-password file.
Nothing else belongs in `~/.config/soyspray/recovery/argocd-admin.vault.yml`;
keep it mode 0600. The existing backup collector has a fixed recovery-input
set, so this new Vault needs a separate private off-laptop copy.

Generate it with `python -m scripts.argocd_admin_vault`; a second generation
requires explicit `--replace`. Use `--refresh-cutoff` just before rotation to
keep the pending credential and renew its UTC timestamp. The helper writes only
encrypted mode-0600 input and prints no values. Losing the file is recoverable
with kubectl and a newly generated private credential through the same operation.

Prepare a private JSON variables file containing `rotate_argocd_admin: true`,
freshly observed `argocd_secret_uid` and `argocd_secret_version`, and a new
`argocd_prechange_path`. Never put credential values in that variables file.

```sh
source soyspray-venv/bin/activate
python -m scripts.argocd_admin_vault --refresh-cutoff
ansible-playbook playbooks/operations/security/rotate-argocd-admin.yml \
  --vault-password-file ~/.config/soyspray/recovery/vault-password \
  -e @/absolute/private/rotation-vars.json --check
# Refresh the Vault cutoff and observed resourceVersion before live execution.
python -m scripts.argocd_admin_vault --refresh-cutoff
ansible-playbook playbooks/operations/security/rotate-argocd-admin.yml \
  --vault-password-file ~/.config/soyspray/recovery/vault-password \
  -e @/absolute/private/rotation-vars.json
make argo-login
```

Check mode performs credential/scope validation and reads; it does not rotate.
Verify the old credential gets 401, the new login works, every non-admin Secret
key is unchanged, Applications are Synced/Healthy and no new warning fires.
Use a newly generated private credential for a required admin rollback.
Never re-enable Kubespray's Argo addon. Route rollback goes through a CI-green
PR and a scoped identity/version guarded operation; never apply a broad install.
