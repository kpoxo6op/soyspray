# Immich Offsite Backup

Backups for Immich using CloudNativePG (database) and AWS CLI (media), managed by ArgoCD.

## Overview

- **Database Backups**: CloudNativePG `ScheduledBackup` for PostgreSQL with native WAL support and PITR capability
- **Media Backups**: Kubernetes CronJob syncing the Immich media PVC to S3 using AWS CLI

## Architecture

### Database Backup (CloudNativePG)

- **Schedule**: Check the YAML
- **Method**: `barmanObjectStore`
- **Destination and credentials**: Defined in the Cluster's `spec.backup.barmanObjectStore`
- **Features**: WAL archiving, PITR support, operator-managed

### Media Backup (CronJob)

- **Schedule**: `30 2 * * *` - 02:30 UTC (14:30 NZST)
- **Method**: AWS CLI `s3 sync` with optimized multipart uploads
- **Source**: Immich library PVC (`immich-library`)
- **Destination**: `s3://$BUCKET_NAME/$MEDIA_PREFIX`
- **Behavior**: Append-only incremental sync (no deletes, aligns with IAM policy)

## Prerequisites

1. **CloudNativePG Operator** deployed in the cluster
2. **Immich** deployed with CloudNativePG-backed database (cluster name: `immich-db`)
3. **AWS S3 bucket** with appropriate IAM permissions:
   - `s3:PutObject`
   - `s3:AbortMultipartUpload`
   - `s3:ListBucket`
4. **Credentials**: Configure `OFFSITE_BACKUP_*` variables in `.env` file

## Credentials

The deployment playbook creates secret `immich-offsite-writer` in the `immich` namespace with:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `BUCKET_NAME`
- `MEDIA_PREFIX`

This secret is used by the media CronJob and can be referenced by the CNPG Cluster's `s3Credentials`.

This will:
1. Load credentials from `.env` and validate them
2. Create the `immich-offsite-writer` Secret in the `immich` namespace
3. Deploy the ArgoCD application

## Inspect Media Before Backup

To see what files will be backed up from the Immich library PVC:

```bash
# Get the Immich server pod name
POD=$(kubectl -n immich get pods -l app.kubernetes.io/name=server -o jsonpath='{.items[0].metadata.name}')

# Explore the media directory structure
kubectl -n immich exec $POD -- ls -lh /usr/src/app/upload

# Check disk usage by directory
kubectl -n immich exec $POD -- sh -c "du -sh /usr/src/app/upload/*"

# Count files being backed up
kubectl -n immich exec $POD -- sh -c "
  echo '=== Total size ===' && \
  du -sh /usr/src/app/upload && \
  echo '' && \
  echo '=== File counts ===' && \
  find /usr/src/app/upload/upload -type f | wc -l && \
  echo 'original files in upload/' && \
  find /usr/src/app/upload/thumbs -type f | wc -l && \
  echo 'thumbnails in thumbs/'
"
```

**Note**: The Immich server mounts the PVC at `/usr/src/app/upload`, while the backup CronJob mounts the same PVC at `/library`. Both point to the same underlying storage.

#### Understanding the Mount Paths

The `/library` path in the backup script is where we mount the `immich-library` PVC inside the backup container:

```
┌─────────────────────────────────────────────┐
│  PVC: immich-library (Longhorn Storage)     │
│  Contains: photos, videos, thumbnails, etc  │
└──────────────┬──────────────────────────────┘
               │
               ├─────────────────┬──────────────────────
               │                 │
               ▼                 ▼
    ┌──────────────────┐  ┌─────────────────────┐
    │  Immich Server   │  │  Backup CronJob     │
    │  Pod             │  │  Pod                │
    ├──────────────────┤  ├─────────────────────┤
    │ Mount Path:      │  │ Mount Path:         │
    │ /usr/src/app/    │  │ /library            │
    │      upload      │  │                     │
    └──────────────────┘  └─────────────────────┘
```

**Key Points:**
- Both containers access the **same physical storage** (the `immich-library` PVC)
- They just mount it at different paths inside their respective containers
- `/library` is configured in `cronjob-media-sync.yaml` as `volumeMounts.mountPath`
- The PVC is defined as `volumes.persistentVolumeClaim.claimName: immich-library`
- We chose `/library` for simplicity - it could be any path like `/backup` or `/data`

### Media Directory Structure

```
/library/                    (PVC root, as seen by backup job)
├── upload/        ✅ BACKED UP - Original photos and videos
├── library/       ✅ BACKED UP - Originals with Storage Template enabled
├── profile/       ✅ BACKED UP - User avatar images
├── thumbs/        ⏭️  SKIPPED - Generated thumbnails (regenerated on restore)
├── encoded-video/ ⏭️  SKIPPED - Transcoded videos (regenerated on restore)
└── backups/       ⏭️  SKIPPED - Metadata dumps (redundant with CNPG backups)
```

## Verification

### Check Media Backups

**CronJob Status:**
```bash
# Check CronJob configuration and last run
kubectl -n immich get cronjob immich-media-offsite-sync

# View recent job executions
kubectl -n immich get jobs --sort-by=.metadata.creationTimestamp

# Check logs from most recent job
kubectl -n immich logs job/$(kubectl -n immich get jobs -l batch.kubernetes.io/job-name -o jsonpath='{.items[-1].metadata.name}')
```

**S3 Verification:**
```bash
# List backed up directories
aws s3 ls s3://immich-offsite-archive-au2/immich/media/

# View most recently modified files (sorted by timestamp)
aws s3 ls s3://immich-offsite-archive-au2/immich/media/ --recursive | sort -k1,2 -r | head -5

# Get summary statistics
aws s3 ls s3://immich-offsite-archive-au2/immich/media/ --recursive --human-readable --summarize | tail -3
```

### Check Database Backups

TODO

## Troubleshooting

### Database Backup Failing

TODO

### Media Sync Failing

TODO

### Manual Trigger

Force a backup job immediately:

TODO

## Database Backup Configuration

Database backups are configured in the `immich-db` CNPG app, not this app. This follows the principle that backup schedules should be managed alongside the database cluster.

### Required Configuration

The `immich-db` Cluster needs backup configuration in `playbooks/yaml/argocd-apps/cnpg/immich-db/immich-db-cluster.yaml`:

```yaml
spec:
  backup:
    retentionPolicy: "60d"
    barmanObjectStore:
      destinationPath: s3://immich-offsite-archive-au2/immich/db/
      s3Credentials:
        accessKeyId:
          name: immich-offsite-writer
          key: AWS_ACCESS_KEY_ID
        secretAccessKey:
          name: immich-offsite-writer
          key: AWS_SECRET_ACCESS_KEY
        region:
          name: immich-offsite-writer
          key: AWS_REGION
```

The `ScheduledBackup` resource is already included in `playbooks/yaml/argocd-apps/cnpg/immich-db/scheduledbackup-db.yaml` and referenced in the immich-db app's kustomization.

**Note**: The deployment playbook automatically creates the `immich-offsite-writer` secret in both `immich` and `postgresql` namespaces.

## Restoration

### Database Restore

TODO

### Media Restore

TODO

2. **Regenerate thumbnails and transcodes**:

After restore, open Immich Web UI → **Administration → Jobs** and run:
- **Thumbnail Generation** - Regenerates all thumbnail variants
- **Video Transcoding** - Regenerates browser-friendly transcodes

Immich will process all originals and recreate the derived content automatically.
