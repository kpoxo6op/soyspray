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
