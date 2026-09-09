# Immich production database

This folder declares the existing Immich PostgreSQL database and its stable
service alias. Argo CD owns both paths as direct, non-pruning Applications.

`production/` renders these existing objects:

- `Cluster/immich-db-a`
- `Secret/immich-app-secret-a`
- `ScheduledBackup/immich-db-daily-a`

`alias/` renders `Service/immich-db-active`. It points to
`immich-db-a-rw.postgresql.svc.cluster.local`.

The production database keeps its current PostgreSQL system identity, image,
PVC, credentials, Barman archive server, and daily backup schedule. Do not
rename or recreate these resources during recovery work.

## Normal checks

Run the maintained application checks from the repository root:

```sh
make status APP=immich FORMAT=json
make check APP=immich
make go
```

Render the database paths directly when reviewing a manifest change:

```sh
kubectl kustomize apps/immich/database/production
kubectl kustomize apps/immich/database/alias
```

Normal delivery is a pull request merged to `main`. The two Applications have
no automated child sync and keep `Prune=false,Delete=false`. Do not delete an
Application, database object, claim, or volume as a rollback action.

## Recovery

Use [`apps/immich/recovery/`](../recovery/) for the isolated recovery check. It
restores into a new namespace and a new database. It does not use this folder's
historical A/B suffix or role overlays, and it does not cut production over to
a restored database.

The production archive writer uses Barman Cloud plugin v0.15.0 and archive
server `immich-db-a-post-ssd-20260506`. Daily base backups run at 04:47 UTC,
WAL archiving uses a five-minute timeout, and retention is owned by the backup
repository. A schedule alone is not restore evidence.
