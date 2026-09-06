# Recovery operations

Use these operations before changing ownership of durable applications. Keep
the existing backup stores until the replacement has passed a real restore.

## Read backup status

```sh
make backup-status
make backup-status FORMAT=json
```

This reads Longhorn volumes, completed backups, backup groups, targets, and CNPG
backup records. It does not read Secrets or change the cluster. Longhorn age starts
at the snapshot time. PostgreSQL base-backup age starts at the backup start time;
it does not show the latest recoverable WAL point. A continuous-archiving condition
does not prove WAL age.

Schedule coverage and successful-backup coverage are separate. Retired claims are
excluded. A failed, unfinished, or incomplete Longhorn backup cannot replace the
last completed backup in this view. Failure counts cover only retained native
records. Target availability and observation times show the backup system's view;
the command does not independently inspect S3 objects.

Restic snapshot observations, restore evidence, and seven-day proof remain
`unknown` until their observation sources are connected. Missing native API data
also appears as `unknown`, with its cause. Exit code 0 means the native observations
were read; it does not mean all data meets the recovery target. Exit code 2 means
an observation source failed or could not be read. For offline checks, use
`python -m scripts.backup_status --input saved-observations.json --format json`.

## Create the S3 store

`provision-s3.yml` creates one private S3 bucket and one IAM user. The user can
manage only its selected prefix (`longhorn/` by default). The bucket has no versioning, archive rule,
or expiry rule. Longhorn owns backup retention. The operation rejects an
existing bucket with versioning or lifecycle rules and never rotates a key.

Run from an authenticated AWS operator session. AWS CloudShell can supply this
session without creating an administrator access key. Prepare its tools:

```bash
python3 -m venv recovery-venv
source recovery-venv/bin/activate
python -m pip install ansible-core==2.18.18 boto3==1.43.62
```

On the laptop, AWS CLI v2 can use the existing console session with temporary
credentials. Keep this operator session separate from backup credentials:

```sh
aws login --profile soyspray-operator --region ap-southeast-2
aws configure set region ap-southeast-2 --profile soyspray-operator
aws configure set credential_process 'aws configure export-credentials --profile soyspray-operator' --profile soyspray-operator-sdk
aws configure set region ap-southeast-2 --profile soyspray-operator-sdk
export AWS_PROFILE=soyspray-operator-sdk
aws sts get-caller-identity
```

Use the SDK profile for Ansible. It invokes the installed CLI to obtain temporary
credentials. Backup workloads use only the dedicated encrypted export. The
operator session can expire without stopping backups.

Install the collection listed in `requirements.yml` as shown below. An initial
`--check` run verifies the account and recipient but skips bucket creation and
the policy for a new user. Run check mode again after bootstrap to inspect
the existing resources.

On the laptop, create an RSA transfer key in a private directory outside Git:

```bash
umask 077
mkdir -p ~/.config/soyspray/recovery
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \
  -out ~/.config/soyspray/recovery/transfer.key
openssl pkey -in ~/.config/soyspray/recovery/transfer.key -pubout \
  -out ~/.config/soyspray/recovery/transfer.pub
```

Copy only `transfer.pub` to the AWS operator environment. Push and check the
branch, then run its playbook there:

```bash
ansible-galaxy collection install -r playbooks/operations/recovery/requirements.yml
ansible-playbook playbooks/operations/recovery/provision-s3.yml \
  -e recovery_account=<verified-account-id> \
  -e recovery_public_key=<path-to-transfer.pub> \
  -e recovery_sealed_credentials=<private-directory>/longhorn-credentials.rsa
```

Copy the encrypted `.rsa` file back to the laptop. Keep the transfer private
key outside the cluster. The export contains only the dedicated Longhorn key.
Do not print decrypted credentials or put them in Git. Keep runtime inputs in
Ansible Vault before installing them in Kubernetes. Keep the Vault password
outside the cluster and retain a separate recovery copy.

A retry uses the existing key and encrypted export. If key creation succeeded
but export failed, the operation stops. Inspect that incomplete bootstrap;
do not replace a key that a running backup may already use.

For Immich, pass `-e @apps/immich/backup/store.yml` and a separate
`recovery_sealed_credentials` path to the same operation. This creates an identity
limited to `immich/` in the recovery bucket. It does not change Longhorn's policy
or the historical archive buckets. Decrypt its export directly into Ansible Vault
with the existing private recovery key. Verify allowed object read/write/delete
and rejected access outside the prefix before deploying a backup workload.

## Check and rollback

Run `ansible-lint` and the playbook syntax check, then `make go`. After the
first apply, repeat the operation and check that it makes no changes. Verify
the bucket settings and test the dedicated identity before adding schedules.

This bootstrap does not change an existing backup bucket, workload, claim, or
backup schedule. To stop later backups, pause their schedules. Retain the
bucket and credentials until a deliberate retirement operation is approved.
Never remove a backup store as a rollback of application code.

## Enable durable volume backups

Keep these inputs in an Ansible Vault file outside Git:

```yaml
recovery_account: '<verified-account-id>'
recovery_region: ap-southeast-2
recovery_bucket: 'soyspray-recovery-au2-<verified-account-id>'
longhorn_s3_credentials:
  AWS_ACCESS_KEY_ID: '<dedicated-key-id>'
  AWS_SECRET_ACCESS_KEY: '<dedicated-secret-key>'
```

`configure-longhorn.yml` resolves the existing Obsidian, Vaultwarden, and Boys
claims and the active small-volume claims listed in the playbook by namespace
and name. It checks the PVC UID and PV CSI binding. It requires healthy, attached Longhorn volumes
with three replicas. It enables filesystem freezing for these volumes and
assigns each claim to its explicit `critical` or `durable-small` group. It keeps their names, claims,
data, and application ownership.

Push the branch and run `make go`. Use the standard inventory and privilege
settings for check mode, then omit `--check` to apply:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/configure-longhorn.yml \
  -e @"${HOME}/.config/soyspray/recovery/longhorn.vault.yml" \
  --vault-password-file ~/.config/soyspray/recovery/vault-password --check
```

The `critical-recent` job runs every 30 minutes and retains 48 backups per
volume. `critical-daily` runs at 14:15 UTC and retains 30 backups per volume.
Both use Longhorn's `backup-force-create` task so a successful check can also
be recorded when data has not changed. Native backup jobs retain the remote
backups separately from their local snapshots. Keep
`auto-cleanup-recurring-job-backup-snapshot` enabled.

The `durable-small-daily` job runs at 15:45 UTC and retains 30 backups. It covers
Home Assistant configuration, Mosquitto, Zigbee2MQTT, BookLore configuration/data
and MariaDB, Dispatcharr, active Jellyfin configuration, LazyLibrarian books and
configuration, qBittorrent configuration, and persistent Redis data. These volumes
keep three replicas. The operation preserves the critical schedules.

No job uses the default group. Database operator volumes, the Immich library,
monitoring data, the retired Jellyfin claim, and node-local media are not selected.
The Speech-to-Phrase and Piper volumes contain downloaded models and generated
training output. Home Assistant stores the source configuration. Unique GI model
and node-local file recovery need separate coverage; this policy does not prove it.

Run the native daily job once after bootstrap to establish initial coverage. Give
each deliberate run a new identifier; retries inspect the same Job:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/backup-daily-now.yml \
  -e recovery_backup_id=initial-small-1
```

This uses Longhorn's generated CronJob template and its native retention policy.
It requires the CronJob's owner UID to match the daily policy. A retry must match
the original template and identity. The completed Job expires after one day;
Longhorn retains backup records and S3 objects under its own policy. Verify a
completed backup for every selected claim with `make backup-status FORMAT=json`.
Restore each database and verify its integrity before accepting recovery coverage.


Check the actual backup results:

```bash
kubectl -n longhorn-system get backuptarget critical-s3
kubectl -n longhorn-system get recurringjobs critical-recent critical-daily
kubectl -n longhorn-system get backups
kubectl -n longhorn-system get jobs
```

The first scheduled run starts at the next half hour. A schedule alone is not
recovery evidence. Require a completed backup for each volume, then perform an
isolated restore. SQLite databases and their WAL files must be restored
together and pass an integrity check. Measure the recovery point and elapsed
restore time. Keep seven days of backup evidence before accepting the
one-hour recovery-point target.

Before a data migration, also export the runtime secrets and configuration
needed to use restored data into encrypted off-cluster inputs. A volume
backup does not preserve a Boys session signing key or CouchDB credentials
stored in a Kubernetes Secret.

## Create a recovery point now

Use `backup-now.yml` before a migration or restore exercise. It uses native
Longhorn Snapshot and Backup resources. The identifier makes a retry refer to
the same recovery point. Its retention belongs to `critical-recent`.

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/backup-now.yml \
  -e recovery_app=boys -e recovery_backup_id=before-migration-1
```

Use `obsidian` or `vaultwarden` for the other critical apps. Choose a new
identifier for a new recovery point. A retry stops on an unhealthy volume or
failed backup. The operation waits for a completed upload; a snapshot alone
does not count as an offsite backup.

## Preserve runtime inputs

`export-runtime.yml` reads the named Boys, Vaultwarden agent, and CouchDB
runtime resources. It encrypts them directly into an off-cluster Ansible Vault
archive. It does not write a plaintext export. Use an absolute archive path
outside this repository and a private Vault password file with mode `0600`.

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/export-runtime.yml \
  -e recovery_runtime_archive="${HOME}/.config/soyspray/recovery/runtime-20260905.vault.yml" \
  -e recovery_vault_password_file="${HOME}/.config/soyspray/recovery/vault-password"
```

A retry retains the existing archive. Use a new filename after a deliberate
credential or runtime configuration change. Keep a separate recovery copy of
the archive and its key. The archive includes the Boys session key and crew
PIN, CouchDB credentials and configuration, and the restricted Vaultwarden
agent login. It does not contain the human vault's master password.

The archive stores the original Kubernetes objects as reference inputs.
Restore only the required data and configuration fields into reviewed
manifests. Do not apply archived UIDs, resource versions, or owner references.
An encrypted runtime archive complements the volume backups; it does not
prove that the application can be restored.

## Inspect an isolated volume restore

For Boys, `make restore-check APP=boys` runs the full isolated workflow and data
checks with automatic guarded cleanup. See the [app guide](../../../apps/boys/README.md#run-an-isolated-restore)
for encrypted inputs, report paths, and evidence limits. The operations below
remain available for deliberate inspection. Automated callers can supply
`recovery_expected_claim_uid` and `recovery_expected_backup_uid` to bind the
restore to prior observations. Cleanup also checks the supplied backup UID.

`restore-volume.yml` restores one completed critical backup into a new
Longhorn claim. It checks the source claim and backup identity first. The
scratch namespace denies ingress and egress. Its inspection container has no
service-account token, host mounts, or public endpoint. The container uses a
pinned Python image and stops after four hours. The disposable volume has one
replica and no selected backup jobs.

Push the branch and run `make go`. Select an actual completed backup name:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/restore-volume.yml \
  -e recovery_app=boys -e recovery_check_id=initial-20260905 \
  -e recovery_backup_name=backup-initial-20260905-boys
```

Use `vaultwarden` or `obsidian` and that app's backup name for the other
critical volumes. A retry reuses the same scratch claim. Use a new check ID
for a fresh restore. The operation rejects an existing namespace or storage
class with different ownership or backup identity. Check mode validates the
source and proposed storage resources; it does not mount data.

The operation waits for Longhorn restore completion before mounting data. It
stops on a reported scheduling failure or faulted volume. Physical free space
does not guarantee scheduling capacity: inspect Longhorn disk reservations
and scheduled volume sizes. Record the failure and clean up that scratch
workspace before retrying.

Copy the restored directory to a private location outside Git for application
checks. The Boys inspector uses UID 1000, the same user as the application,
so it can read private pre-migration backup files without extra capabilities.
If a check used an older inspector, clean up that scratch workspace and use a
new check identifier. The inspection container does not run the app, so the copy includes
the SQLite database and any WAL files without concurrent app writes:

```bash
install -d -m 700 ~/.local/state/soyspray/restores/boys-initial-20260905
kubectl -n restore-boys-initial-20260905 cp --retries=3 inspect:/data \
  ~/.local/state/soyspray/restores/boys-initial-20260905/data
```

Use SQLite's backup API on the copied database before test writes. Require
`PRAGMA integrity_check` to return `ok`. Verify the existing Boys identities,
PIN hashes, sessions, dates, and events against the restored data. Start the
same app version with the archived runtime inputs, using only a loopback
endpoint. Verify the restricted Vaultwarden identity can decrypt a record.
For the stock Vaultwarden and CouchDB servers, use `start-restored-app.yml`
after copying the untouched restore. It uses the same pinned image versions
as the current deployments. It retains network isolation and mounts only the
scratch claim. CouchDB needs the encrypted runtime archive:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/start-restored-app.yml \
  -e recovery_app=obsidian -e recovery_check_id=initial-20260905 \
  -e recovery_couchdb_image=OBSERVED_PINNED_COUCHDB_IMAGE \
  -e @"${HOME}/.config/soyspray/recovery/runtime-20260905.vault.yml" \
  --vault-password-file ~/.config/soyspray/recovery/vault-password
kubectl -n restore-obsidian-initial-20260905 port-forward pod/app 15985:5984
```

For Vaultwarden, create a temporary RSA certificate outside Git. The current
Bitwarden CLI requires HTTPS. This certificate is for the isolated loopback
test and is not added to the system trust store:

```bash
restore_tls_dir="${HOME}/.local/state/soyspray/restores/vault-tls"
install -d -m 700 "$restore_tls_dir"
umask 077
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj /CN=localhost \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign' \
  -keyout "$restore_tls_dir/key.pem" -out "$restore_tls_dir/cert.pem"
```

Select `recovery_app=vaultwarden`, pass
`-e recovery_tls_directory="$restore_tls_dir"` and
`-e recovery_vaultwarden_image=PINNED_STOCK_IMAGE` to `start-restored-app.yml`, and
forward `18443:8443`. Point the separate test CLI data directory at
`https://localhost:18443`. Set `NODE_EXTRA_CA_CERTS="$restore_tls_dir/cert.pem"`
only for that CLI process. TLS uses Vaultwarden's native `ROCKET_TLS` setting.
Keep certificate verification enabled.

Use a separate Bitwarden CLI data directory for the test login. Read real
notes, attachment chunks, and vault records. Keep private data out
of logs, screenshots, and Git. Record the backup recovery point, restore
duration, results, and any unknown checks outside the repository.

The volume restore alone is not acceptance evidence. Do not move stateful
ownership until application checks pass. Keep production claims, credentials,
and offsite backups during this operation.

To stop a scratch server before copying its files or changing its pod
configuration, run `stop-restored-app.yml` with the same app and check ID. It
deletes only that verified app pod and retains the inspector and restored
claim. A failed or interrupted file copy is not a recovery candidate. Retry
the copy after the app stops, and check the complete result before using it.

After saving the results, remove only that disposable workspace:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/recovery/cleanup-restore.yml \
  -e recovery_app=boys -e recovery_check_id=initial-20260905
```

Cleanup checks ownership labels and claim bindings, then uses UID
preconditions to delete the scratch namespace and storage class. It waits
for the disposable backing volume to disappear. It retains offsite backups
and production claims. A failed restore can also use this cleanup operation;
retain its error evidence first.

## Read private restore evidence

`make backup-status FORMAT=json` reads the Application inventory, native backup
records, and private reports under `~/.local/state/soyspray/restores/` (or
`XDG_STATE_HOME`). `make status APP=boys FORMAT=json` uses the same observations
for claims named by the Application's `soyspray.vip/data-claims` annotation.
Missing mappings remain unknown; folder names do not create app inventory.

A restore is accepted only when its report matches the observed PVC and PV UIDs,
contains completed data checks and cleanup, and confirms that original resources
were unchanged. Status shows the last attempt separately from the last accepted
restore, with its age and tested image. A later failed or interrupted attempt
remains visible. Invalid or unreadable reports make the latest attempt uncertain.
Only selected metadata is printed; private data and raw error text are omitted.

This is historical evidence for that image and storage identity. It does not
prove a human login, current runtime behavior, or seven days of RPO coverage.
Reports stay on the operator machine and are not uploaded into the cluster.
Keep the off-cluster recovery keys separately.

## Schedule monthly isolated restore checks

The laptop can run the three maintained restore checks from one native systemd
user timer. The timer runs on the first day of each month at 03:00 and uses
`Persistent=true`, so a powered-off laptop runs the missed check after it
starts. It uses the existing encrypted files under
`~/.config/soyspray/recovery/`; it does not create credentials or use a model.

Install the user units only after reviewing the service and timer templates:

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  playbooks/operations/recovery/install-restore-check-schedule.yml
systemctl --user status soyspray-restore-check.timer
```

The service runs one shared repository gate, then invokes
`make restore-check APP=boys`, `APP=vaultwarden`, and
`APP=obsidian-livesync` in that order. It validates the JSON report after each
command. A result is accepted only when the report belongs to that app and
schedule run, has `status: passed`, and has `cleanup: completed`. A failed app
with completed cleanup does not block the other apps. A missing report or
incomplete cleanup stops the schedule with a nonzero result and retains all
reports for inspection.

The schedule summary stays under
`~/.local/state/soyspray/restores/schedule/<run-id>/report.json`; command logs
are private files in the same folder. The scheduler serializes monthly runs
with a private lock. Use `journalctl --user -u soyspray-restore-check.service`
and the summary report to inspect a run.

For offline checks, `scripts.app_status` accepts `--input` for Applications and
`--backup-input` for saved native backup observations. `scripts.backup_status`
accepts an observation bundle through `--input`. Offline checks make no cluster
requests and do not scan private reports unless `--restore-dir` is supplied.
Saved observations establish the recorded storage identities, not the current
cluster binding. Use live commands to check current bindings.

The monthly runner checks one exact Git revision with the full gate. Each app then runs `make -o check restore-check APP=...`, which retains its Git and Ansible preflight without repeating the full gate. A changed revision stops the run. On interruption, the runner allows fifteen minutes for the active restore to finish guarded cleanup.

Set `-e recovery_schedule_enabled=false` on the installer to disable the timer and stop its service with guarded cleanup. Use `-e recovery_schedule_run_now=true` to verify the installed service once.

Each scheduled runner checks the saved successful full-check report against its
Git revision before reusing that result. It still runs deployment preflight.
Standalone restore commands run the full check normally.

## Backup-age observations

Install the laptop's two-minute observation timer with
`ansible-playbook playbooks/operations/recovery/install-evidence-schedule.yml`.
It reads the critical backup recording rule, completed Immich Restic snapshots,
and private restore reports. Records append to
`~/.local/state/soyspray/evidence/operations.jsonl`. Missing or stale sources
remain unknown with a cause. Immich age starts at the paired database dump.

The timer uses no model. It does not backfill laptop downtime. Seven full days
of actual observations are required for release review. Inspect failures with
`journalctl --user -u soyspray-operations-evidence.service`; disable with the
same installer and `-e evidence_enabled=false`. The model review remains paused.

## PostgreSQL archive migration

`migrate-cnpg-backup.yml` switches the selected existing database to the installed
Barman plugin in one guarded API request. It checks the database UID, PostgreSQL
system ID, destination and retention, waits for health, and creates a named base
backup. Use `-e cnpg_database=immich -e cnpg_backup_id=NAME` with the standard
inventory and privilege options. Run check mode first to validate against the API.

Push the matching database manifests before applying. Immich has no automatic
sync. After the migration and base backup pass, run
`reconcile-immich-database.yml -e cnpg_revision=BRANCH` to sync its existing
resources without hooks or pruning. After merge, repeat with `cnpg_revision=HEAD`.
Verify archive continuity and production access before closing the migration.

For Authentik, first use `select-authentik-database.yml -e cnpg_revision=BRANCH`.
It pauses database self-heal so the archive switch remains atomic. Then run
`migrate-cnpg-backup.yml -e cnpg_database=authentik -e cnpg_backup_id=NAME`.
After verification, select the branch again with `-e cnpg_sync=true`. After
merge, select `HEAD`; this restores the existing automatic sync policy.
