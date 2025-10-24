# CNPG Database Recovery Test - FAILED

## Test Result: FAILURE

Recovery test performed on 2025-10-24 to restore immich-db from S3 backup.

## Failure Summary

The recovery process completed successfully from a technical standpoint - CNPG correctly restored the database from S3 to the specified point in time. However, the restored data was invalid:

1. Restored database named `app` instead of expected `immich`
2. The `app` database contained no data (empty)
3. All S3 backups from Oct 12 onwards contained only this empty `app` database
4. The original working `immich` database with actual data was never backed up to S3

## Root Cause

The CNPG cluster was originally configured with `database: immich`, but at some point between Oct 7-12, 2025, the database was recreated as `app`. All subsequent backups captured only this empty `app` database. The working Immich instance was running against a local database that was never properly backed up to S3.

## Cleanup Actions

All invalid backups were deleted from S3:

```bash
# Deleted all database backups
aws s3 rm s3://immich-offsite-archive-au2/immich/db/ --recursive

# Deleted all media backups
aws s3 rm s3://immich-offsite-archive-au2/immich/media/ --recursive
```

Backups deleted as junk. Starting over with fresh backup configuration.

## Prerequisites

Restorer and writer AWS credentials configured in `.env`:

## Recovery Process

### 1. Create Recovery Branch

```bash
git checkout -b immich-cnpg-restore
```

### 2. Identify Latest Backup in S3

```bash
# List latest WAL files
aws s3 ls s3://immich-offsite-archive-au2/immich/db/immich-db/wals/0000000100000003/ | tail -5

# Result:
# 2025-10-24 15:47:33   16777216 0000000100000003000000E1
# 2025-10-24 15:52:32   16777216 0000000100000003000000E2
# 2025-10-24 15:56:55   16777216 0000000100000003000000E3
```

Latest WAL timestamp: `2025-10-24 15:56:55 NZDT` (UTC+13)

### 3. Update ArgoCD Application Target

Edit `playbooks/yaml/argocd-apps/cnpg/immich-db-application.yaml`:

```yaml
sources:
  - repoURL: "https://github.com/kpoxo6op/soyspray.git"
    targetRevision: "immich-cnpg-restore"  # Point to recovery branch
    path: playbooks/yaml/argocd-apps/cnpg/immich-db
```

### 4. Configure Cluster for Recovery

Edit `playbooks/yaml/argocd-apps/cnpg/immich-db/immich-db-cluster.yaml`:

#### Change Bootstrap from initdb to recovery

```yaml
bootstrap:
  recovery:
    source: immich-db-backup
    recoveryTarget:
      targetTime: "2025-10-24 15:56:51+13:00"  # Last available transaction
  # initdb:  # Comment out initdb section
  #   database: immich
  #   owner: immich
  #   ...
```

#### Add externalClusters with restorer credentials

```yaml
externalClusters:
  - name: immich-db-backup
    barmanObjectStore:
      destinationPath: s3://immich-offsite-archive-au2/immich/db/
      serverName: immich-db  # Must match backup directory name
      s3Credentials:
        accessKeyId:
          name: immich-offsite-restorer  # Use restorer credentials
          key: AWS_ACCESS_KEY_ID
        secretAccessKey:
          name: immich-offsite-restorer
          key: AWS_SECRET_ACCESS_KEY
        region:
          name: immich-offsite-restorer
          key: AWS_REGION
```

#### Comment out backup section (avoid WAL archive conflict)

```yaml
# backup:
#   retentionPolicy: "60d"
#   barmanObjectStore:
#     destinationPath: s3://immich-offsite-archive-au2/immich/db/
#     s3Credentials:
#       accessKeyId:
#         name: immich-offsite-writer
#         ...
```

### 5. Set Recovery Target Time Correctly

**Critical**: Recovery target must not exceed the last transaction in the archive.

```bash
# Check last transaction in S3
aws s3api head-object --bucket immich-offsite-archive-au2 \
  --key immich/db/immich-db/wals/0000000100000003/0000000100000003000000E3 \
  --query 'LastModified' --output text

# Result: 2025-10-24T02:56:55Z (UTC)
# Convert to NZDT: 2025-10-24 15:56:55+13:00
```

**During recovery, PostgreSQL logs show the actual last transaction time**:

```
last completed transaction was at log time 2025-10-24 02:56:51.979798+00
```

Set `targetTime` to match or be before this timestamp:

```yaml
recoveryTarget:
  targetTime: "2025-10-24 15:56:51+13:00"  # Adjusted to last transaction
```

If target is too far in the future:
```
FATAL: recovery ended before configured recovery target was reached
```

### 6. Commit and Push Changes

```bash
git add playbooks/yaml/argocd-apps/cnpg/
git commit -m "Configure CNPG immich-db to restore from S3 backup"
git push -u origin immich-cnpg-restore
```

### 7. Delete Existing Database

```bash
argocd app delete immich-db --yes
```

Verify cleanup:

```bash
kubectl get cluster -n postgresql
kubectl get pods -n postgresql
kubectl get pvc -n postgresql
```

### 8. Deploy Recovery Configuration

```bash
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/deploy-argocd-apps.yml --tags immich-db
```

### 9. Track Recovery Progress

#### Check Cluster Status

```bash
kubectl get cluster -n postgresql
```

Expected: `STATUS: Setting up primary`

#### Check Pod Status

```bash
kubectl get pods -n postgresql
```

Expected: `immich-db-1-full-recovery-xxxxx   1/1     Running`

#### Monitor Recovery Logs

```bash
# Watch recovery progress
kubectl logs -n postgresql immich-db-1-full-recovery-xxxxx -c full-recovery --tail=20 -f

# Check specific recovery phases
kubectl logs -n postgresql immich-db-1-full-recovery-xxxxx -c full-recovery | \
  grep -E "point-in-time recovery|Target backup found|restored log file|redo done"
```

Key log messages:

1. Backup discovery:
```
Target backup found: backup-20251023044700
```

2. Base backup restore:
```
Starting barman-cloud-restore
```

3. Point-in-time recovery start:
```
starting point-in-time recovery to 2025-10-24 02:56:51+00
```

4. WAL replay progress:
```
restored log file "0000000100000003000000B1" from archive
restored log file "0000000100000003000000B2" from archive
...
restored log file "0000000100000003000000E3" from archive
```

5. Recovery completion:
```
redo done at 3/E30010C8
last completed transaction was at log time 2025-10-24 02:56:51.979798+00
recovery has paused
```

## Outcome

Recovery mechanism validated - CNPG successfully performed PITR from S3. However, the restored database was unusable due to invalid backups. All S3 backups containing the empty `app` database were deleted.

Media and DB backups were deleted as junk.

## Next Steps

Start over with proper database configuration and backup validation:

1. Ensure CNPG cluster is configured with correct database name (`immich`)
2. Verify backups contain actual data before relying on them
3. Test recovery process with valid backups
