# Immich isolated restore

This workflow restores one completed paired Restic snapshot into a new
namespace. It creates a disposable Longhorn claim, CNPG database, Redis Pod,
and Immich server. It creates no external Service or Ingress.

The default check does not read the production namespace, production database,
production Secret, production claim, or production volume. Recovery credentials
come from the encrypted off-cluster file at
`~/.config/soyspray/recovery/immich-backup.vault.yml`. The Vault password stays
in the separate `vault-password` file. Do not pass either secret on the command
line.

Run the check from the pushed repository revision. Name the target kubeconfig
and inventory explicitly:

```sh
SOYSPRAY_RECOVERY_KUBECONFIG="$HOME/.kube/config" \
SOYSPRAY_RECOVERY_INVENTORY="$PWD/kubespray/inventory/soycluster/hosts.yml" \
  make restore-check APP=immich
```

Set `SOYSPRAY_COMPARE_PRODUCTION=1` only when an optional before/after identity
comparison is useful. That comparison reads production metadata. It is not a
recovery input and is disabled by default.

The workflow selects the newest Restic snapshot with host `immich` and tag
`restore-candidate`. It ignores pending snapshots. It runs `restic restore
--verify`, checks the paired PostgreSQL dump and file trees, restores the dump
into a fresh database, and compares database file references with the paired
manifest. It records actual asset, album, and user counts.

All runtime images are pinned by digest. Scratch workloads use normal scheduler
placement and normal registry pulls. NetworkPolicy denies cross-namespace and
private-network access from application Pods. Only the Restic Pod can reach
public HTTPS. CNPG management traffic retains its explicit cluster API access.

The runner writes private logs and `report.json` under
`~/.local/state/soyspray/restores/immich/`. Passed and failed runs delete only a
namespace whose purpose, app, check ID, and UID match. The wrapper also runs
guarded cleanup after `SIGINT` or `SIGTERM`.

To retry cleanup for a known check ID:

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  apps/immich/recovery/cleanup.yml \
  -e recovery_check_id=CHECK_ID
```

A successful check proves recovery through the existing Kubernetes, Longhorn,
CNPG, DNS, and registry infrastructure. It does not prove total-cluster recovery
and does not authorize a production cutover. A useful release check must contain
a disposable non-personal asset; a zero-asset snapshot is not photo-recovery
evidence.
