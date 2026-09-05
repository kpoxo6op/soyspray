# Recovery operations

Use these operations before changing ownership of durable applications. Keep
the existing backup stores until the replacement has passed a real restore.

## Create the S3 store

`provision-s3.yml` creates one private S3 bucket and one IAM user. The user can
manage only the `longhorn/` prefix. The bucket has no versioning, archive rule,
or expiry rule. Longhorn owns backup retention. The operation rejects an
existing bucket with versioning or lifecycle rules and never rotates a key.

Run from an authenticated AWS operator session. AWS CloudShell can supply this
session without creating an administrator access key. Prepare its tools:

```bash
python3 -m venv recovery-venv
source recovery-venv/bin/activate
python -m pip install ansible-core==2.18.18 boto3==1.43.62
```

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

## Check and rollback

Run `ansible-lint` and the playbook syntax check, then `make go`. After the
first apply, repeat the operation and check that it makes no changes. Verify
the bucket settings and test the dedicated identity before adding schedules.

This bootstrap does not change an existing backup bucket, workload, claim, or
backup schedule. To stop later backups, pause their schedules. Retain the
bucket and credentials until a deliberate retirement operation is approved.
Never remove a backup store as a rollback of application code.

## Enable critical volume backups

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
claims by namespace and name. It requires healthy, attached Longhorn volumes
with three replicas. It enables filesystem freezing for these volumes and
assigns them to the explicit `critical` group. It keeps their names, claims,
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

No job uses the default group. Database operator volumes, the Immich library,
monitoring data, and retired claims are not selected by this operation.

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
checks. The inspection container does not run the app, so this copy includes
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
`-e recovery_tls_directory="$restore_tls_dir"` to `start-restored-app.yml`, and
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
