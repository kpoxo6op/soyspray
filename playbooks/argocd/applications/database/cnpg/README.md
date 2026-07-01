# CNPG Immich Database A/B Setup

**Generator-driven layout** with single-copy overlays and ApplicationSet-injected suffixes for A/B failover and PITR restore.

## Architecture
- **Base + Overlays**: Shared cluster config + single role overlays (initdb/prod/restore)
- **ApplicationSets**: Generate the active DB app + active alias app via nameSuffix injection
- **Alias Service**: `immich-db-active` ExternalName switches A/B
- **NameRefs**: Backups track generated cluster names
- **DB Secret**: Managed by DB stack, independent of alias lifecycle

## Operations
- **Bootstrap**: See `docs/init-bootstrap/README.md`
- **A/B Restore**: See `docs/restore-exercise/README.md`
- **Kustomize Validation**: See `docs/kustomize-validation/README.md`

**Quick rules:** Generate only the active role by default; edit only targetTime file for restores; keep one prod cluster with backups; delete inactive PVCs before restore.
**Note:** ApplicationSets disable automation - sync apps explicitly to avoid ownership conflicts.
Generated apps intentionally omit Argo resource finalizers and set
`preserveResourcesOnDeletion: true`, so deleting a generated Application does
not prune CNPG clusters, secrets, backups, or the active alias Service.

## Argo Cleanup Safety

Before reducing the generated app matrix, first sync these ApplicationSets and
confirm the generated Applications no longer carry
`resources-finalizer.argocd.argoproj.io`:

```bash
kubectl -n argocd get app \
  immich-db-a-initdb immich-db-a-prod immich-db-a-restore \
  immich-db-b-initdb immich-db-b-prod immich-db-b-restore \
  immich-db-active-a immich-db-active-b \
  -o json | jq -r '.items[] | [.metadata.name, (.metadata.finalizers // [])] | @tsv'
```

Do not delete or stop generating inactive apps until that check is clean.

The default rendered set is:

```text
immich-db-a-initdb
immich-db-active-a
```

To prepare a B-side restore, temporarily add the needed B-side role to
`apps/applicationset-immich-db.yaml`, set the restore target time, then sync the
generated restore app. To flip the alias, change
`apps/applicationset-immich-alias.yaml` from `active: a` to `active: b` in the
same reviewed change.

## Key Components
- `base/`: Shared cluster-base for external CNPG references
- `immich-db/base/`: DB secret and cluster config (vectors, monitoring, S3 backup)
- `immich-db/overlays/{initdb,prod,restore}/`: Single-copy overlays per role
- `immich-db-active/overlays/{active-a,active-b}/`: Alias switching
- `apps/`: ApplicationSets inject active -a/-b suffixes via kustomize.nameSuffix
- `docs/`: Bootstrap/restore guides

## Quick Commands
```bash
# Bootstrap
kubectl apply -f apps/applicationset-*.yaml
argocd app sync cnpg-operator immich-db-active-a immich-db-a-initdb

# Status
kubectl -n postgresql get cluster,backup,scheduledbackup

# A→B restore
$EDITOR immich-db/overlays/restore/target-time.yaml
# Add letter=b, role=restore to apps/applicationset-immich-db.yaml first.
argocd app sync immich-db-b-restore immich-db-active-b
kubectl -n immich rollout restart deployment/immich-server

# Quick validation checks
kubectl kustomize immich-db/overlays/initdb >/dev/null && echo "✓ initdb"
kubectl kustomize immich-db/overlays/prod   >/dev/null && echo "✓ prod"
kubectl kustomize immich-db/overlays/restore>/dev/null && echo "✓ restore"

# Spot-check with suffix (simulate Argo)
cd immich-db/overlays/initdb && \
  kustomize edit set namesuffix -- -a && \
  kubectl kustomize . | grep -E 'name: immich-db-a|kind: (Cluster|Backup|ScheduledBackup)' && \
  git restore kustomization.yaml
```

**S3**: `s3://immich-offsite-archive-au2/immich/db/` (writer/restorer secrets)
**Extensions**: vectors, cube, earthdistance + custom search_path
