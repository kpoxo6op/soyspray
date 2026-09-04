# Recovery operations

Use these operations before changing ownership of durable applications. Keep
the existing backup stores until the replacement has passed a real restore.

## Create the S3 store

`provision-s3.yml` creates one private S3 bucket and one IAM user. The user can
manage only the `longhorn/` prefix. The bucket has no versioning, archive rule,
or expiry rule. Longhorn owns backup retention. The operation rejects an
existing bucket with versioning or lifecycle rules and never rotates a key.

Run from an authenticated AWS operator session. AWS CloudShell can supply this
session without creating an administrator access key. Install Ansible Core
2.18 and the collection listed in `requirements.yml` in that environment.

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
