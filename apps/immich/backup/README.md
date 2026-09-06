# Immich paired backup

This folder defines the suspended paired backup CronJob for Immich. The
existing `immich-offsite-backup` Application keeps its current identity and
source path and includes this folder from its Kustomization.

The CronJob runs every 30 minutes when enabled. It uses `Forbid` concurrency
and runs three ordered stages:

1. Copy `dump.sh`, `dump.sql`, and `backup.sh` from the pinned script bundle.
2. Run the PostgreSQL dump with the database connection from the
   `immich-paired-backup` Secret.
3. Run the Restic backup against the same snapshot and the original content
   under `/usr/src/app/upload`.

The paired job stays suspended until a real backup and isolated restore pass. The Secret must contain exactly these operational keys:

```text
PGHOST
PGPORT
PGDATABASE
PGUSER
PGPASSWORD
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION
RESTIC_REPOSITORY
RESTIC_PASSWORD
```

`PGHOST` must come from Immich's authoritative `DB_URL` connection. Do not
derive it from the legacy `DB_HOSTNAME` setting. `RESTIC_PASSWORD` is mounted
as a file. It is not passed as an environment variable. The job disables
service-account token mounting.

The database image is PostgreSQL 16.10 and the Restic image is 0.18.1. The
script image is the tested immutable digest recorded in `kustomization.yaml`.
The library PVC is mounted read-only at `/usr/src/app/upload`, and required pod
affinity keeps the job with the Immich server because the claim is RWO.

Enable the schedule only after the root Ansible work creates the Secret and an
isolated backup and restore check passes. Keep the existing nightly media job
until the paired replacement is verified.

## Operator commands

Run `make go` on the pushed branch first. Activate `soyspray-venv` and use the
standard inventory, `--become --become-user=root --user ubuntu` options with
these Ansible playbooks:

- `apps/immich/backup/bootstrap.yml --vault-password-file /private/vault-password -e @/private/immich-backup.vault.yml`
- `apps/immich/backup/deploy.yml -e immich_backup_revision=PUSHED_BRANCH`
- `apps/immich/backup/run-job.yml -e immich_backup_operation=initialize -e immich_backup_run_id=UNIQUE_ID -e immich_backup_evidence_dir=/private/evidence`
- `apps/immich/backup/run-job.yml -e immich_backup_operation=backup -e immich_backup_run_id=UNIQUE_ID -e immich_backup_evidence_dir=/private/evidence`

Initialize a new repository once. An existing repository makes initialization
fail without replacing it. The run command requires a suspended CronJob and no
active scheduled Job. Run manual operations one at a time. Logs remain in the
private evidence directory; the temporary Job is removed after success or failure.
After an operator process is interrupted, inspect its named Job before retrying.

The bootstrap derives PostgreSQL fields from the active `DB_URL` and compares
the username and password with the existing database Secret. Restic inputs come
from Ansible Vault. Check mode performs validation; repeated runs reject changed
credentials and preserve the existing Secret.

After merge, return the Application to `HEAD` with the existing merged-branch
handoff runbook. Verify its exact source comparison before deleting the branch.
