# Immich

Immich stores photo metadata in PostgreSQL and original files in its existing
`immich-library` claim. Keep the database identity, storage, and access settings
when changing deployment ownership.

## Paired recovery backup

The backup operation is packaged from `backup/`. It is not registered for
scheduled deployment yet. The current application and nightly S3 copy continue
to use their existing definitions.

The operation exports a database snapshot and its required original-file paths,
then backs up the dump with `upload`, `library`, and `profile`. The path list and
dump use the same PostgreSQL transaction snapshot. Other original files are kept,
including files that have no current database record. Generated thumbnails,
transcodes, and the app's separate dump directory are excluded.

Only a successful Restic backup whose saved tree contains every required file
gets the `restore-candidate` tag. A deleted or moved file can make a backup
ineligible even when Restic reports success. The snapshot time is the database
dump start in UTC. The fixed hostname is `immich`; retention groups by hostname
so changes to paths cannot create separate retention groups.

The policy keeps 48 recent successful snapshots and 30 daily snapshots. Restic
owns retention. Do not apply S3 object expiry to its repository. Retention failures
fail the job but do not invalidate a complete, verified restore candidate.
External libraries require explicit mounts and inclusion rules before this
operation can accept them.

Run `python3 apps/immich/tests/test_backup.py` on a host with Docker for the native
image integration checks. They use disposable containers and a local repository,
including a photo fixture, an album, a concurrent database edit, deleted and moved
files, unreadable files, and a failed dump. CI runs these checks for affected
Immich changes; manual full-repository CI includes them.

Use the pinned upstream PostgreSQL and Restic images in the integration check.
The Restic image already includes jq. Keep the repository password outside the
cluster in the encrypted recovery inputs. Never place it in Git or CI fixtures.

References: [Immich backup order](https://docs.immich.app/administration/backup-and-restore/),
[PostgreSQL synchronized dumps](https://www.postgresql.org/docs/16/app-pgdump.html),
and [Restic retention](https://restic.readthedocs.io/en/stable/060_forget.html).

## Image changes and promotion

CI builds the script bundle and runs the native recovery tests using files copied
from that exact image. The bundle is a short init step; PostgreSQL and Restic still
run their pinned upstream images. Runtime scripts are not loaded from ConfigMaps.

A runtime source merge publishes the tested bundle to GHCR and opens a draft
promotion containing its digest in `backup/kustomization.yaml`. Source-only and
test-only merges do not change a running Job. Any configuration that requires a
new script version must be reviewed in the same promotion. The first promotion
records the image before a Job is registered. Do not enable the schedule until a
real backup and isolated restore pass.

The native image workflow is called by affected-app CI. Manual full-repository CI
checks the image without publishing. To request a tested rebuild and promotion:

```sh
gh workflow run immich-backup-image.yml --ref main -f publish=true
```

Roll back the digest and dependent configuration together. Keep all existing
claims, database identities, and S3 archives during recovery adoption.
