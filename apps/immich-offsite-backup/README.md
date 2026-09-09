# Immich offsite backup

This Argo application runs Immich's paired database and original-file backup.
The runtime scripts and recovery code live in `apps/immich-offsite-backup/manifests/runtime/` and
`apps/immich/recovery/`; this directory owns the native Application package and
its service account.

Use `make check APP=immich-offsite-backup` for the paired-backup manifest
checks and `make diff APP=immich-offsite-backup` for a read-only live
comparison. Use `make restore-check APP=immich` for the maintained isolated
database and media restore. Merge changes to `main` for Argo delivery.

The backup uses the existing private writer Secret and S3 repository. Restic
owns retention. Preserve the database identity, archive identity, schedule,
credentials, and `immich-library` claim. A completed upload is not restore
proof; only the private restore-candidate and isolated restore evidence count.
