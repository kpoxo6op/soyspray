# Immich isolated restore

This folder verifies one completed paired Restic snapshot in a new namespace.
It never mounts `immich-library`, connects to `immich-db-active`, or creates an
external Service or Ingress. The source Secret is copied into the scratch
namespace through Kubernetes Secret references and is never printed.

Run a check from the repository root with a new short identifier:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  apps/immich/recovery/restore.yml \
  -e recovery_check_id=20260906-a
```

The procedure selects the newest Restic snapshot with host `immich` and tag
`restore-candidate`. It restores the dump and the `upload`, `library`, and
`profile` trees into a new Longhorn PVC. It then uses the pinned PostgreSQL
image, Immich `v2.3.1`, and Redis `8.2.1` in the scratch namespace. Database
table counts and canonical row hashes are compared with a second restore of
the same dump. Every restored file is hashed against `restic dump`, and an
internal ping and version request checks the server.

The playbook records production Deployment, PVC, database Service, and CNPG
Cluster identities before and after the check. A failure removes only a
namespace with matching ownership labels and its UID. If Ansible is stopped,
run the guarded cleanup with the same identifier:

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  apps/immich/recovery/cleanup.yml \
  -e recovery_check_id=20260906-a
```

Successful checks retain the scratch namespace for review. Cleanup is a
separate deliberate operation. A successful isolated check does not authorize
an application restore, a production claim change, or a database cutover.
