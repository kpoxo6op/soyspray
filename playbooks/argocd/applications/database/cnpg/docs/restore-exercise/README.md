<!--
playbooks/yaml/argocd-apps/cnpg/docs/restore-exercise/README.md
Standard A/B restore with single timestamp edit and generator-based apps.
-->

# Immich DB A/B DR — Restore Exercise

This procedure restores the inactive letter from S3 to a **UTC** point‑in‑time and flips the alias.

## Fixed references

* Bucket: `s3://immich-offsite-archive-au2/immich/db/`
* `serverName`: `immich-db`
* Restore creds: secret `immich-offsite-restorer`
* Backup creds: secret `immich-offsite-writer`
* Stable URL for Immich:

  `postgresql://immich:immich@immich-db-active.postgresql.svc.cluster.local/immich`

## A → B

**Detach before delete** during promotion to prevent pruning the restored cluster.

1. Verify alias points to A:

```bash
kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'
```

2. Remove any existing B:

```bash
argocd app delete immich-db-b-prod --yes || true
argocd app delete immich-db-b-restore --yes || true
kubectl -n postgresql delete cluster immich-db-b --ignore-not-found
kubectl -n postgresql delete pvc -l cnpg.io/cluster=immich-db-b
```

3. Set **UTC** target:

```bash
$EDITOR playbooks/argocd/applications/database/cnpg/immich-db/overlays/restore/target-time.yaml
```

4. Recreate **B from S3**:

```bash
argocd app sync immich-db-b-restore
kubectl -n postgresql get pods -l cnpg.io/cluster=immich-db-b -w &
kubectl -n postgresql logs -f -l cnpg.io/cluster=immich-db-b --all-containers=true
```

5. Validate DB:

```bash
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-b -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) FROM assets;"
```

6. Flip alias to B and restart Immich:

```bash
argocd app delete immich-db-active-a --yes
argocd app sync immich-db-active-b
kubectl -n immich rollout restart deployment/immich-server
kubectl -n immich rollout status  deployment/immich-server
```

7. Promote B to prod (enable backups under prod overlay):

```bash
kubectl -n postgresql annotate cluster/immich-db-b argocd.argoproj.io/instance-
argocd app delete immich-db-b-restore --yes
argocd app sync immich-db-b-prod
```

8. Decommission A:

```bash
argocd app delete immich-db-a-prod --yes || true
kubectl -n postgresql delete cluster immich-db-a --ignore-not-found
```

## B → A

Repeat the same flow with A/B swapped:

* Remove any existing A: `argocd app delete immich-db-a-prod --yes || true`
* Edit `playbooks/yaml/argocd-apps/cnpg/immich-db/overlays/restore/target-time.yaml`
* `argocd app sync immich-db-a-restore`
* Watch logs: `kubectl -n postgresql get pods -l cnpg.io/cluster=immich-db-a -w & kubectl -n postgresql logs -f -l cnpg.io/cluster=immich-db-a --all-containers=true`
* `argocd app delete immich-db-active-b --yes && argocd app sync immich-db-active-a`
* `kubectl -n immich rollout restart deployment/immich-server`
* Promote with `argocd app sync immich-db-a-prod`
* Decommission B: `argocd app delete immich-db-b-prod --yes || true`

## Rules

* Edit only the **targetTime** file before each restore.
* Keep exactly **one** production letter synced with backups.
* Keep the alias Application synced at all times.
* Delete the inactive letter and its PVCs before every restore.
