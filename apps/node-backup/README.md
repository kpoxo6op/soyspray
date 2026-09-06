# Node-local recovery backup

This package creates a daily Restic snapshot from the durable node-local paths
that were verified on `node-0`. The daily CronJob is enabled at 03:00 Auckland time after a real
backup and isolated restore passed. It uses a tested immutable image digest.

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

Restic retains 30 daily snapshots, grouped by host.

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

The dedicated workflow builds the image and runs these tests with the packaged
Python and Restic binaries. A main-branch run publishes the tested image;
deployment requires a separate digest promotion. Each snapshot includes a
content manifest with file hashes and the SQLite integrity result. Image changes require a separate tested digest promotion.

## Operations

Store the restricted `node/` identity in
`~/.config/soyspray/recovery/node-backup.vault.yml` as `node_backup_credentials`.
The bootstrap rejects credential mismatches and preserves an existing Secret.

Use `make deploy APP=node-backup REVISION=BRANCH` for the standard branch preview.
Return to `REVISION=HEAD` after merge. Run `apps/node-backup/run.yml` through the
standard Ansible inventory with `node_backup_run_id` and a private
`node_backup_evidence_dir`. It requires an inactive CronJob temporarily suspended through Git and removes
its temporary Job after saving the log.

Use `make restore-check APP=node-backup SNAPSHOT=ID` to check the S3 repository structure,
restore the snapshot in a private laptop directory, verify each file against its
saved hash, and check Jellyfin SQLite integrity and row counts. The command removes
restored files and retains a private report under `~/.local/state/soyspray/restores`.
This does not prove playback; check the existing Jellyfin playback command separately.

The first real restore verified 9,562 files, all saved hashes, and Jellyfin SQLite
integrity and row counts. Operator evidence is private. A successful backup log
and its snapshot ID must be retained with each manually accepted restore.
