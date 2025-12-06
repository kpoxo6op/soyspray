# Immich DB Restore Test — Second Immich Instance

This procedure restores database B from S3 to a **UTC** point‑in‑time and connects a second Immich instance to validate the restore. Production Immich remains connected to database A and continues running normally.

## Fixed references

* Bucket: `s3://immich-offsite-archive-au2/immich/db/`
* `serverName`: `immich-db-a`
* Restore creds: secret `immich-offsite-restorer`
* Backup creds: secret `immich-offsite-writer`
* Production Immich URL: `postgresql://immich:immich@immich-db-active.postgresql.svc.cluster.local/immich`
* Test Immich URL: `postgresql://immich:immich@immich-db-b-rw.postgresql.svc.cluster.local/immich`

## Overview

This exercise:
* Restores database B from S3 backups (STANDARD storage, no GLACIER restore needed)
* Both databases A and B coexist simultaneously
* Production Immich continues using database A (no changes)
* Test Immich instance connects to database B for validation
* Backups continue running normally on database A
* Database B remains in restore mode (no backups enabled)

## Prerequisites

* Database A running in production with backups enabled
* `immich-restore-test` ArgoCD application deployed (not synced yet)
* Target restore time set in `target-time.yaml`

## Restore Procedure

1. Verify production setup:

```bash
# Check production database A is running
kubectl -n postgresql get cluster immich-db-a

# Verify alias points to A (production)
kubectl -n postgresql get svc immich-db-active -o jsonpath='{.spec.externalName}{"\n"}'
# Expected: immich-db-a-rw.postgresql.svc.cluster.local

# Check production Immich is healthy
kubectl -n immich get pods -l app.kubernetes.io/name=immich-server
```

2. Set UTC target time:

```bash
$EDITOR playbooks/argocd/applications/database/cnpg/immich-db/overlays/restore/target-time.yaml
```

Current target: `2025-11-29 23:59:59+00:00` (last day with STANDARD storage)

3. Remove any existing database B (if present):

```bash
argocd app delete immich-db-b-prod --yes || true
argocd app delete immich-db-b-restore --yes || true
kubectl -n postgresql delete cluster immich-db-b --ignore-not-found
kubectl -n postgresql delete pvc -l cnpg.io/cluster=immich-db-b
```

4. Restore database B from S3:

```bash
argocd app sync immich-db-b-restore
kubectl -n postgresql get pods -l cnpg.io/cluster=immich-db-b -w &
kubectl -n postgresql logs -f -l cnpg.io/cluster=immich-db-b --all-containers=true
```

5. Validate restored database B:

```bash
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-b -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) FROM assets;"
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT MAX(\"createdAt\") FROM assets;"
```

6. Deploy test Immich instance connected to database B:

```bash
# Deploy the ArgoCD application
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags immich-restore-test

# Sync the application
argocd app sync immich-restore-test

# Monitor test Immich startup
kubectl -n immich-restore-test get pods -w
kubectl -n immich-restore-test logs -f deployment/immich-server
```

7. Access and validate test Immich:

```bash
# Check test Immich is accessible
curl -k https://immich-restore-test.soyspray.vip/api/server/ping
# Expected: {"res":"pong"}

# Access via browser
# URL: https://immich-restore-test.soyspray.vip
```

8. Compare data between production and test:

```bash
# Production database A
POD_A=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-a -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD_A" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) as prod_count FROM assets;"

# Test database B
POD_B=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db-b -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD_B" -- psql -h localhost -U immich -d immich -c "SELECT COUNT(*) as test_count FROM assets;"
```

## Results

**Test Date**: 2025-12-05 (UTC)

### ✅ Successful Restore

1. **Database B Restore**: Successfully restored from S3 backup to point-in-time `2025-11-29 23:59:59+00:00`
   - Database cluster created and healthy
   - All extensions loaded correctly (vectors, cube, earthdistance)
   - Asset count matched expected restore point

2. **Media PVC Restore**: Successfully restored media files from S3 to test instance PVC
   - 255 files synced from S3 (174 DEEP_ARCHIVE + 81 STANDARD)
   - All original files verified and accessible
   - File integrity confirmed via SHA256 checksums

3. **Test Immich Instance**: Successfully deployed and connected to database B
   - Instance accessible at `https://immich-restore-test.soyspray.vip`
   - API responding correctly
   - Connected to `immich-db-b-rw` service

4. **Thumbnail Regeneration**:
   - Majority of thumbnails regenerated successfully (~248 out of 254 assets)
   - Regeneration required multiple attempts for some assets
   - Some assets succeeded on first attempt, others required retries
   - All thumbnails eventually restored after repeated regeneration attempts

### Notes

- Production Immich (database A) continued running normally throughout the test
- No impact on production operations
- Test instance fully validated restore procedure
- See `playbooks/argocd/applications/backups/immich-offsite-backup/docs/recovery-test-2nd-immich/THUMBNAIL-GENERATION-ERROR-REPORT.md` for detailed thumbnail regeneration analysis

## Cleanup

After validation is complete, clean up the test resources:

```bash
# Delete test Immich instance
argocd app delete immich-restore-test --yes

# Delete database B restore (keeps it in restore mode, no backups)
argocd app delete immich-db-b-restore --yes

# Optionally delete database B cluster and PVCs
kubectl -n postgresql delete cluster immich-db-b --ignore-not-found
kubectl -n postgresql delete pvc -l cnpg.io/cluster=immich-db-b
```

## Important Notes

* Production Immich (immich namespace) is never modified
* Database A continues running with backups enabled
* Database B remains in restore mode (no backups, no promotion to prod)
* Both databases coexist during testing
* Test Immich uses separate namespace (`immich-restore-test`) and hostname
* No GLACIER restore needed - using STANDARD storage backups
* Media restore is separate - test instance uses its own PVC

## Differences from Production Restore

* No alias switching - production stays on A
* No promotion to prod - B stays in restore mode
* No decommissioning - A continues running
* Second Immich instance for validation
* Separate namespace and hostname for test instance
