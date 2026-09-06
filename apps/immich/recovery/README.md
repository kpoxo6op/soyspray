# Immich isolated restore

This folder verifies one completed paired Restic snapshot in a new namespace.
It reads the production A identities (`immich-db-a` and the
`immich-db-active` alias), then uses a separate database, Redis Pod, PVC, and
Immich server. It never mounts `immich-library` or creates an external Service
or Ingress.

Run a check from the repository root with a new short identifier:

```sh
source soyspray-venv/bin/activate
apps/immich/recovery/run.sh 20260906-a \
  -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  -e recovery_db_password='use-a-private-password' \
  -e recovery_server_image_digest='ghcr.io/immich-app/immich-server:v2.3.1@sha256:...' \
  -e recovery_expected_asset_count=0 -e recovery_expected_album_count=0 \
  -e recovery_expected_user_count=1
```

The procedure selects the newest Restic snapshot with host `immich` and tag
`restore-candidate`. It runs `restic restore --verify` into a new Longhorn PVC
and checks the dump plus the `upload`, `library`, and `profile` trees. It
restores the dump into a fresh CNPG database with a dedicated owner that can
create the required extensions, then checks the real `asset`, `album`, and
`user` counts. The isolated server uses the production database image and
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
production claim change, or a database cutover. The server image digest and a
new scratch database password are mandatory inputs. Current paired-backup
evidence is 0 assets, 0 albums, and 1 user; use different counts only for a
snapshot with verified source evidence.
