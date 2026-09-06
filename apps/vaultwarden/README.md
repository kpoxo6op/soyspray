# Vaultwarden

Open <https://vault.soyspray.vip> from the LAN or Tailscale. Keep the human vault
and restricted agent account separate. Sign in with your human email and master password. Registration is closed.
Official Bitwarden clients use **Self-hosted** with this server URL; see the
[client setup guide](https://bitwarden.com/help/change-client-environment/).
Keep the human master password outside Kubernetes. Use the
[master-password guide](https://bitwarden.com/help/master-password/) when changing it;
a volume restore cannot recover a forgotten master password.

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
Run `make restore-check APP=vaultwarden` from a committed, pushed branch. It runs
`make go`, selects the newest complete critical-s3 backup, restores a separate
volume, and starts the observed pinned stock image with network isolation. It
checks SQLite with its WAL, recorded attachment sizes, and the restricted record's login
fields through a private TLS endpoint. It never uses the human master password.
The original claim, PV, deployment, and agent Secret must remain unchanged.
Guarded cleanup runs after a failed restore attempt too.

Defaults are `~/.config/soyspray/recovery/vaultwarden.vault.yml` and
`vault-password`. Both must be outside the checkout. Override inputs or select
an older completed backup with:

```sh
soyspray-venv/bin/python -m apps.vaultwarden.restore_check \
  --vault-file /private/vaultwarden.vault.yml \
  --vault-password-file /private/vault-password --backup BACKUP_NAME
```

The command needs `bw`, `openssl`, cluster access, and the repo venv. It serializes
local checks and uses loopback port 18443. CLI state and copied data are temporary;
private reports stay under `~/.local/state/soyspray/restores/vaultwarden/`.
`make backup-status FORMAT=json` reads that evidence. Failed cleanup is a failed
check: inspect its private log and retry the guarded cleanup procedure.
Repeat monthly. Attachment presence does not prove human attachment decryption,
and this check does not compare an older snapshot with later live edits.
Upgrade the testing image in a separate reviewed change. The current pinned build
is `1.37.2-fa2566d1`. It includes the upstream
[password-change compatibility fix](https://github.com/dani-garcia/vaultwarden/commit/fa2566d14fc745937ce104011475eca9e6c7a6f6)
for newer web clients. Stable 1.37.2 predates that fix. Select a stable release that
includes it, then test that image against an isolated restored vault before
promotion. Replacing the current pin with stable 1.37.2 would remove this behavior.

## Restricted reader

The `automation@vault.soyspray.vip` account can view the existing shared item in
`Hays timesheets`. It cannot edit or manage the collection. The app-local
`agent_secret.py` keeps this one-item limit. The installed `agent-secret` command
and `scripts/agent-secret` still use the same command path and private CLI state.

With `bw`, `kubectl`, and cluster access, check the restricted record silently:

```sh
agent-secret read hays-online-timesheets >/dev/null
```

Without redirection, this command prints the username and password as plaintext
JSON. Keep that output out of logs, GitHub, and shell arguments. A process with
the same cluster access can read the agent password; this does not grant the
human master password.

For the existing Hays workflow, run `scripts/hays-open-submitted-timesheet`. It
opens the latest submitted timesheet in its dedicated Chrome profile and leaves
the page visible. It does not submit or change a timesheet.

If recovery requires a new agent enrollment, create or restore the `Soyspray`
organization and `Hays timesheets` collection from the human account. Temporarily
allow invitations through a reviewed manifest change, while keeping sign-ups
closed. Invite only the restricted identity with **View items** and password
viewing. Complete registration with its private runtime input, compare member
fingerprints, and confirm membership from the human account. Share only
`hays-online-timesheets`, close invitations, and run the silent check above.
Restore an existing identity from backup before considering new enrollment.

Restore checks use `scripts/restore_common.py` for the private workspace, lock, subprocess limits, report, and guarded cleanup. Application data checks remain in this folder. The [monthly restore schedule](../../playbooks/operations/recovery/README.md) runs the same maintained command and validates its report.
