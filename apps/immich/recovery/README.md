# Immich isolated restore

This folder verifies one completed paired Restic snapshot in a new namespace.
It reads the production A identities (`immich-db-a` and the
`immich-db-active` alias), then uses a separate database, Redis Pod, PVC, and
Immich server. It never mounts `immich-library` or creates an external Service
or Ingress.

Run `make restore-check APP=immich` from the pushed repository checkout.
The shared runner checks deployment prerequisites, takes a private lock, creates
a unique check ID and scratch password, and saves private logs. It uses the
existing off-cluster Immich Vault inputs. Do not pass passwords on the command line.

The procedure selects the newest Restic snapshot with host `immich` and tag
`restore-candidate`. It runs `restic restore --verify` into a new Longhorn PVC
and checks the dump plus the `upload`, `library`, and `profile` trees. It
restores the dump into a fresh CNPG database with a dedicated owner that can
create the required extensions, then compares the restored database file references with the paired manifest
and checks that every referenced file exists. The report records actual asset,
album, and user counts. The isolated server uses the production database image and
Immich `v2.3.1`, plus Redis `8.2.1`.

The playbook records production Deployment, PVC, database Service, CNPG
Cluster, and PV identities before and after the check. Passed and failed runs
remove only a namespace with matching ownership labels and its UID. A private
`report.json` is written after cleanup. The wrapper also runs guarded cleanup
when it receives `SIGINT` or `SIGTERM`.

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  apps/immich/recovery/cleanup.yml \
  -e recovery_check_id=20260906-a
```

A successful isolated check does not authorize an application restore, a
production claim change, or a database cutover. The maintained runner pins the server digest and generates a new scratch password. The initial snapshot has 0 assets, 0 albums, and 1 user. Its historical files
are preserved; an empty asset table does not prove photo recovery.

Scratch file consumers use native affinity to the production server's node.
This reuses its exact cached image and avoids moving the scratch RWO claim
between jobs. Production claims are not mounted. The restore creates empty
marker files only for omitted generated folders (`thumbs`, `encoded-video`,
`backups`), as documented by [Immich](https://docs.immich.app/administration/system-integrity/#missing-immich-files).
These folders are initialized; their contents are not claimed as recovered.
