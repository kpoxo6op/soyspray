# Obsidian LiveSync

Open Obsidian with the existing LiveSync settings. All clients use
`https://obsidian.soyspray.vip` and database `obsidian-main`. Keep the existing
CouchDB credentials on each client. Note editing and synchronization stay in
Obsidian; this repository manages the server and its recovery.

The active single-writer Deployment keeps its name
`obsidian-livesync-couchdb-hostpath-rescue`. It uses the 10Gi Longhorn claim
`obsidian-livesync-couchdb-rescue-longhorn`, not hostPath storage. Preserve both
names, `/opt/couchdb/data`, the database, service names, host, and credentials.
The native root protects the Application, project, namespace, and claim against
pruning and deletion. Parking must retain data; retirement needs a separate
explicit Ansible operation.

```sh
make check APP=obsidian-livesync
make status APP=obsidian-livesync FORMAT=json
make diff APP=obsidian-livesync
make deploy APP=obsidian-livesync REVISION=YOUR_PUSHED_BRANCH
```

Push before deployment. The command runs the full local checks, Ansible bootstrap,
and native root. After merge, return to HEAD with `make deploy APP=obsidian-livesync`.
Check the exact Argo comparison, original pod and storage UIDs, database contents,
authenticated access, and client synchronization. Ingress migration and image
pinning remain separate changes.

## Recovery inputs

Bootstrap preserves two existing Secrets in `obsidian`. It restores only a missing
Secret with native create, which rejects a competing creation. All input checks
finish before writes. Matching inputs make no writes. Different credentials or
backup settings stop the operation; bootstrap cannot rotate or redirect them.

Keep these mappings in an off-cluster Ansible Vault variables file:

- `obsidian_couchdb_identity`: `adminUsername`, `adminPassword`, `cookieAuthSecret`,
  and `erlangCookie` for `obsidian-livesync-couchdb`.
- `obsidian_offsite_identity`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `AWS_REGION`, `BUCKET_NAME`, and `BACKUP_PREFIX` for `obsidian-offsite-writer`.

With the standard inventory and privilege options from AGENTS.md, run
`apps/obsidian-livesync/bootstrap.yml -e @/private/obsidian.vault.yml --ask-vault-pass`,
first with `--check`. Keep recovery keys outside the cluster. Restore data before
starting clients against a replacement cluster.

Longhorn keeps 48 recent backups every 30 minutes and 30 daily backups. Use the
[isolated recovery operations](../../playbooks/operations/recovery/README.md) to
start stock CouchDB on a scratch claim with archived configuration and credentials.
Compare restored notes with the real local vault. Report attachment recovery as
unknown when there is no attachment to restore. Preserve evidence of existing
missing chunks; do not repair or remove notes during an ownership migration.
The legacy offsite export remains active with its existing destination during
the recovery observation period. Its retirement needs a separate reviewed change.

Run `make restore-check APP=obsidian-livesync` from a committed, pushed branch.
It runs the full gate, selects a complete critical-s3 backup, creates a separate
claim, and starts the observed CouchDB digest with network isolation. The original
claim, PV, deployment, credentials, and configuration must remain unchanged.
Guarded cleanup runs after a failed attempt too.

The command reads `obsidian_couchdb_identity` from
`~/.config/soyspray/recovery/obsidian.vault.yml`, with `vault-password` alongside it.
It checks the identity against live and the committed configuration against the
live ConfigMap before any writes. Offsite writer keys are not used. Inputs must
stay outside Git. Override them or select a specific completed backup with:

```sh
soyspray-venv/bin/python -m apps.obsidian-livesync.restore_check \
  --vault-file /private/obsidian.vault.yml \
  --vault-password-file /private/vault-password --backup BACKUP_NAME
```

CouchDB credentials must authenticate against the restored server. The check reads
plain note chunks, including embedded legacy Eden chunks, and compares UTF-8 byte
lengths with stored sizes. Missing chunks fail unless the same incomplete note
revision and missing chunks also exist in the live vault. The report keeps that
incomplete coverage visible. Binary attachments and legacy note formats remain
unknown; no data is invented or repaired to make the check pass.

Private reports stay under `~/.local/state/soyspray/restores/obsidian-livesync/`.
`make backup-status FORMAT=json` shows the counts and coverage limits. Temporary
credentials are removed with the working directory; note content is never written
to a local file. Repeat monthly. If cleanup fails, inspect its private log and use
the guarded cleanup operation with the report's check ID.

`make smoke APP=obsidian-livesync` remains unknown until a maintained command
covers the client sync journey. A successful upload or isolated database read
does not prove two-client sync, attachment recovery, or seven-day recovery-point age.

Restore checks use `scripts/restore_common.py` for the private workspace, lock, subprocess limits, report, and guarded cleanup. Application data checks remain in this folder. The [monthly restore schedule](../../playbooks/operations/recovery/README.md) runs the same maintained command and validates its report.
