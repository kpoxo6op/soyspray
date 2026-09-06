# Node-local recovery backup

This package creates a daily Restic snapshot from the durable node-local paths
that were verified on `node-0`. The CronJob is committed with `spec.suspend:
true`. Root must promote the tested image digest, create the credential Secret,
run one real backup and isolated restore, then deliberately enable the schedule.

The backup runs on `node-0` and reads these paths through read-only host mounts:

- `/srv/media/jellyfin-data/data`
- `/srv/media/jellyfin-data/metadata`
- `/srv/media/jellyfin-data/plugins`
- `/srv/media/jellyfin-data/root`
- `/srv/media/downloads/books`

The original `data/jellyfin.db`, `jellyfin.db-wal`, and `jellyfin.db-shm` files
are never copied. The Python SQLite backup API writes a consistent shadow
`jellyfin/data/jellyfin.db` into the temporary backup tree. The script runs
`PRAGMA integrity_check`, records SHA-256 hashes, checks the Restic file list,
and writes `/work/reports/report.json`. A failed Restic command leaves a failed
report and returns a non-zero status.

The backup does not include caches, transcodes, reproducible voice models,
large media trees, or broad host configuration such as `/etc`. The two unique
voice models are on the laptop pCloud path and require a separate local backup
operation. No additional durable node-local unit or configuration file was
proven for inclusion in this package.

The image uses the existing pinned Python 3.13 Alpine base. It installs the
Restic 0.18.1 Linux amd64 binary from the upstream release with a pinned
SHA-256 checksum. The image is run as root because the verified Jellyfin files
are root-owned. The container has no Kubernetes API token and has no writable
host mount.

## Credentials

The Secret `media/node-backup-credentials` must provide these keys to the
CronJob:

- `RESTIC_REPOSITORY`
- `RESTIC_PASSWORD`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`

The script receives `RESTIC_PASSWORD_FILE` as a mounted file path. Do not put
password or access-key values in manifests, reports, test fixtures, or logs.

## Checks

Run the unit and local recovery tests from the repository root:

```text
python3 apps/node-backup/tests/test_backup.py
```

The tests use a concurrent SQLite writer and a temporary local Restic
repository. They verify the restored database integrity and the absence of the
original WAL and shared-memory files. The test is local only. It does not use
cluster mounts or upload to an off-cluster repository.

The dedicated workflow builds the image and runs these tests. The `pending`
image reference in the suspended CronJob is a bootstrap value. Replace it with
the digest from a tested image before any deployment or schedule enablement.
