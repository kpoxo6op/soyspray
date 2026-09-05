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

`make restore-check APP=obsidian-livesync` and `make smoke APP=obsidian-livesync`
remain unknown until maintained app commands cover these procedures. A successful
backup schedule or upload does not prove a restore or seven-day recovery-point age.

## One-time native adoption

After a recent restore, record the original claim UID from its recovery evidence.
Use the standard Ansible inventory and privilege options to run `adopt.yml` with
`-e obsidian_adoption_claim_uid=VERIFIED_ORIGINAL_UID`, first with `--check`.
The operation requires the known idle Application, original claim, and matching
Longhorn binding. It removes only Argo cascading finalizers with a resource-version
guard. Then deploy the pushed branch and verify the original resources and data.
Keep old definitions until that verification succeeds.
