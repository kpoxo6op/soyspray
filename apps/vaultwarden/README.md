# Vaultwarden

Open <https://vault.soyspray.vip> from the LAN or Tailscale. Keep the human vault
and restricted agent account separate. The [vault guide](../../kubernetes/vaultwarden/README.md)
explains normal use, client setup, and the existing Hays helper.

The native root owns the existing Application and AppProject. It preserves the
namespace, `vaultwarden-data` claim, `/data` directory, server keys, host, and pinned
stock image. Application, project, namespace, and PVC protections retain data
when the app is parked. The namespace has an explicit manifest, so its protection
annotations are applied as resource settings. Retirement needs a separate explicit
Ansible operation.

```sh
make check APP=vaultwarden
make diff APP=vaultwarden
make status APP=vaultwarden FORMAT=json
make deploy APP=vaultwarden REVISION=YOUR_PUSHED_BRANCH
```

Deployment uses Ansible bootstrap and the native root after the full local checks.
After merge, run `make deploy APP=vaultwarden` to return to HEAD. Verify the exact
Argo comparison, unchanged image and resource identities, private access, and
restricted agent access. An automated human-login smoke check remains unknown.

## Recovery inputs

Normal bootstrap preserves `vaultwarden-agent-login`. To restore a missing Secret,
supply `vaultwarden_agent_email` and `vaultwarden_agent_master_password` from an
off-cluster Ansible Vault file. Restore the original restricted agent credentials;
this operation does not enroll an account or generate or rotate its password.
Matching inputs make no writes. Different inputs stop before writes. Native create
rejects a competing Secret creation. Check mode validates inputs and skips create.
The human master password never belongs in these inputs or Kubernetes.

With the standard inventory and privilege options from AGENTS.md, run
`apps/vaultwarden/bootstrap.yml -e @/private/vaultwarden.vault.yml --ask-vault-pass`,
first with `--check`. Keep the Vault password and a separate recovery copy outside
the cluster. Restore the data volume and server keys before using restored access.

The critical Longhorn policy keeps 48 recent backups every 30 minutes and 30 daily
backups. Use the [isolated recovery procedure](../../playbooks/operations/recovery/README.md)
to check SQLite integrity, encrypted records and attachments, and restricted-record
decryption. Human unlock and seven-day recovery-point proof remain separate checks.
`make restore-check APP=vaultwarden` remains unknown until that procedure has a
maintained app command. Upgrade the testing image in a separate reviewed change.
