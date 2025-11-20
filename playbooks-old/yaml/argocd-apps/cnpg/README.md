# CNPG Immich Database A/B Setup

**Generator-driven layout** with single-copy overlays and ApplicationSet-injected suffixes for A/B failover and PITR restore.

## Architecture
- **Base + Overlays**: Shared cluster config + single role overlays (initdb/prod/restore)
- **ApplicationSets**: Generate 6 DB apps (A/B x 3 roles) + 2 alias apps via nameSuffix injection
- **Alias Service**: `immich-db-active` ExternalName switches A/B
- **NameRefs**: Backups track generated cluster names
- **DB Secret**: Managed by DB stack, independent of alias lifecycle

## Operations
- **Bootstrap**: See `docs/init-bootstrap/README.md`
- **A/B Restore**: See `docs/restore-exercise/README.md`
- **Kustomize Validation**: See `docs/kustomize-validation/README.md`

**Quick rules:** Edit only targetTime file; keep one prod cluster with backups; delete inactive PVCs before restore.
**Note:** ApplicationSets disable automation - sync apps explicitly to avoid ownership conflicts.

## Key Components
- `base/`: Shared cluster-base for external CNPG references
- `immich-db/base/`: DB secret and cluster config (vectors, monitoring, S3 backup)
- `immich-db/overlays/{initdb,prod,restore}/`: Single-copy overlays per role
- `immich-db-active/overlays/{active-a,active-b}/`: Alias switching
- `apps/`: ApplicationSets inject -a/-b suffixes via kustomize.nameSuffix
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
