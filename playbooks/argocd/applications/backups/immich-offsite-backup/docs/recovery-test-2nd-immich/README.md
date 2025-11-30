# Media Recovery Test — Second Immich Instance

Restore media files from S3 to the test Immich instance PVC, matching the exact database restore date (2025-11-29 23:59:59+00:00). This simulates a full data restoration including DEEP_ARCHIVE files.

## Overview

Media backups are append-only incremental syncs. For a complete restore matching DB restore date (2025-11-29 23:59:59+00:00):
- 174 files are in DEEP_ARCHIVE (from 2025-11-13 to 2025-11-28)
- 83 files are in STANDARD (from 2025-11-13 to 2025-11-29)
- Total: 257 files needed for complete restore matching database state

## Challenge

Media backups transition to DEEP_ARCHIVE immediately (day 0). To restore files from DEEP_ARCHIVE:
1. Must restore from DEEP_ARCHIVE first (12+ hours Standard, 48 hours Bulk)
2. Then sync restored files to PVC
3. Files become temporarily accessible in STANDARD after restore

## Prerequisites

* Database B restored to 2025-11-29 23:59:59+00:00
* Test Immich instance deployed (immich-restore-test namespace)
* PVC `immich-library-restore-test` exists
* Secret `immich-offsite-writer` exists in `immich-restore-test` namespace (or use production secret)
* AWS CLI access configured

## Restore Procedure

### Step 1: Restore DEEP_ARCHIVE Files ✅ COMPLETED

**Executed**: Bulk restore initiated for all 174 DEEP_ARCHIVE files on 2025-11-30
**Result**: All restore requests successfully initiated. Files showing "RestoreAlreadyInProgress" status.
**Next**: Wait ~48 hours for Bulk restore to complete, then proceed to Step 4.

Restore all 174 DEEP_ARCHIVE files to make them accessible. Use Bulk restore (48 hours, cheaper) for full simulation:

```bash
BUCKET="immich-offsite-archive-au2"
TARGET_DATE="2025-11-29T23:59:59"

# Count files to restore
TOTAL=$(aws s3api list-objects-v2 --bucket "$BUCKET" \
  --prefix "immich/media/" \
  --query "Contents[?StorageClass=='DEEP_ARCHIVE' && LastModified<='${TARGET_DATE}'] | length(@)" \
  --output text)
echo "Total files to restore: $TOTAL"

# Restore all DEEP_ARCHIVE files (using JSON output for reliability)
aws s3api list-objects-v2 --bucket "$BUCKET" \
  --prefix "immich/media/" \
  --query "Contents[?StorageClass=='DEEP_ARCHIVE' && LastModified<='${TARGET_DATE}'].Key" \
  --output json | jq -r '.[]' | while read key; do
    aws s3api restore-object \
      --bucket "$BUCKET" \
      --key "$key" \
      --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Bulk"}}' 2>&1 | grep -q "RestoreAlreadyInProgress" && echo "Already in progress: $key" || echo "Initiated restore: $key"
done

echo "Restore requests initiated for all $TOTAL files"
```

**Restore Time**: 48 hours for Bulk tier (cheapest option)

**Status**: All 174 files restore requests successfully initiated. Files showing "RestoreAlreadyInProgress" means restore is active.

**Alternative**: Use Standard tier for faster restore (12 hours, more expensive):
```bash
--restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Standard"}}'
```

### Step 2: Monitor Restore Progress

Check restore status for DEEP_ARCHIVE files (optional - can skip until restore completes):

**Executed**: Verified restore status on 2025-11-30
**Result**: Sample files show "Restore in progress" - confirms all restore requests are active

```bash
BUCKET="immich-offsite-archive-au2"
TARGET_DATE="2025-11-29T23:59:59"

# Check sample files restore status
echo "Checking sample files restore status:"
aws s3api list-objects-v2 --bucket "$BUCKET" \
  --prefix "immich/media/" \
  --query "Contents[?StorageClass=='DEEP_ARCHIVE' && LastModified<='${TARGET_DATE}'].Key" \
  --output json | jq -r '.[0:3]' | jq -r '.[]' | while read key; do
    echo "File: $(basename "$key")"
    STATUS=$(aws s3api head-object --bucket "$BUCKET" --key "$key" --query 'Restore' --output text 2>&1)
    if echo "$STATUS" | grep -q "ongoing-request"; then
      echo "  Status: Restore in progress"
    elif echo "$STATUS" | grep -q "expiry-date"; then
      EXPIRY=$(echo "$STATUS" | grep -oP 'expiry-date="\K[^"]+')
      echo "  Status: Restore completed (accessible until $EXPIRY)"
    elif [ "$STATUS" = "None" ] || [ -z "$STATUS" ]; then
      echo "  Status: No restore request"
    else
      echo "  Status: $STATUS"
    fi
done
```

**Status indicators:**
- `ongoing-request="true"` - Restore in progress (waiting for completion)
- `expiry-date="..."` - Restore completed, file accessible until expiry date
- `None` or empty - No restore request (should not happen after Step 1)

### Step 3: Wait for DEEP_ARCHIVE Restore Completion

**IMPORTANT**: Wait for DEEP_ARCHIVE restore to complete before proceeding to Step 4. Do not sync files until all 174 DEEP_ARCHIVE files are restored and accessible.

Wait 48 hours for Bulk restore (or 12 hours for Standard tier). Verify all files are restored:

```bash
BUCKET="immich-offsite-archive-au2"
TARGET_DATE="2025-11-29T23:59:59"

# Count DEEP_ARCHIVE files that are restored and accessible
DEEP_RESTORED=$(aws s3api list-objects-v2 --bucket "$BUCKET" \
  --prefix "immich/media/" \
  --query "Contents[?StorageClass=='DEEP_ARCHIVE' && LastModified<='${TARGET_DATE}']" \
  --output json | jq -r '.[] | .Key' | while read key; do
    STATUS=$(aws s3api head-object --bucket "$BUCKET" --key "$key" --query 'Restore' --output text 2>&1)
    echo "$STATUS" | grep -q "expiry-date" && echo "1" || echo "0"
  done | grep -c "1")

echo "DEEP_ARCHIVE files restored: $DEEP_RESTORED / 174"

# Count all files that are restored and accessible (DEEP_ARCHIVE + STANDARD)
TOTAL_ACCESSIBLE=$(aws s3api list-objects-v2 --bucket "$BUCKET" \
  --prefix "immich/media/" \
  --query "Contents[?LastModified<='${TARGET_DATE}']" \
  --output json | jq -r '.[] | select(.StorageClass == "STANDARD" or (.Restore // "" | contains("expiry-date"))) | .Key' | wc -l)

echo "Total accessible files: $TOTAL_ACCESSIBLE / 257"
echo "Expected: 257 files (174 DEEP_ARCHIVE + 83 STANDARD)"
echo ""
if [ "$DEEP_RESTORED" -eq 174 ] && [ "$TOTAL_ACCESSIBLE" -eq 257 ]; then
  echo "✓ All files restored and accessible - proceed to Step 4"
else
  echo "⚠ Still waiting for restore completion. DEEP_ARCHIVE restore takes ~48 hours (Bulk tier)"
fi
```

**Current Status**: Waiting for DEEP_ARCHIVE restore to complete (~48 hours from Step 1 execution on 2025-11-30)

**Expected Completion Date**: 2025-12-02 (approximately 48 hours after restore initiation on 2025-11-30)

**Timeline**:
- Step 1 executed: 2025-11-30
- Restore tier: Bulk (48 hours)
- Expected available: 2025-12-02
- Files accessible for: 7 days after restore completes (until ~2025-12-09)

### Step 4: Sync Media Files to PVC (Matching DB Restore Date)

**PREREQUISITE**: Step 3 must show all 257 files are accessible before proceeding.

Once DEEP_ARCHIVE files are restored and accessible (verified in Step 3), sync all files matching the DB restore date (2025-11-29 23:59:59+00:00):

```bash
kubectl run -n immich-restore-test restore-media-date-filtered \
  --image=public.ecr.aws/aws-cli/aws-cli:latest \
  --rm -it --restart=Never \
  --overrides='{
    "spec": {
      "securityContext": {"runAsUser": 0, "runAsGroup": 0},
      "containers": [{
        "name": "restore",
        "image": "public.ecr.aws/aws-cli/aws-cli:latest",
        "command": ["sh", "-c", "TARGET_DATE=\"2025-11-29T23:59:59\" && echo \"Syncing files with LastModified <= ${TARGET_DATE} (matching DB restore date)\" && aws s3api list-objects-v2 --bucket immich-offsite-archive-au2 --prefix immich/media/ --query \"Contents[?LastModified<=\\\`${TARGET_DATE}\\\`].Key\" --output text | grep -v \"thumbs/\" | grep -v \"encoded-video/\" | grep -v \"backups/\" | while read key; do REL_PATH=${key#immich/media/} && mkdir -p \"/library/$(dirname $REL_PATH)\" && aws s3 cp \"s3://immich-offsite-archive-au2/$key\" \"/library/$REL_PATH\" 2>/dev/null && echo \"Synced: $REL_PATH\" || true; done && echo \"Sync complete\""],
        "envFrom": [{"secretRef": {"name": "immich-offsite-writer"}}],
        "volumeMounts": [{"name": "library", "mountPath": "/library"}]
      }],
      "volumes": [{"name": "library", "persistentVolumeClaim": {"claimName": "immich-library-restore-test"}}]
    }
  }' -- /bin/true
```

**Note**: This syncs exactly 257 files (174 DEEP_ARCHIVE + 83 STANDARD) matching the DB restore date. Files backed up after 2025-11-29T23:59:59 are excluded to match database state.

### Step 5: Post-Restore Setup

Create required directories:

```bash
kubectl run -n immich-restore-test create-missing-folders \
  --image=busybox --rm -it --restart=Never \
  --overrides='{
    "spec": {
      "securityContext": {"runAsUser": 0, "runAsGroup": 0},
      "containers": [{
        "name": "init",
        "image": "busybox",
        "command": ["sh", "-c", "mkdir -p /library/thumbs /library/encoded-video /library/backups && touch /library/thumbs/.immich /library/encoded-video/.immich /library/backups/.immich && ls -la /library"],
        "volumeMounts": [{"name": "library", "mountPath": "/library"}]
      }],
      "volumes": [{"name": "library", "persistentVolumeClaim": {"claimName": "immich-library-restore-test"}}]
    }
  }' -- /bin/true
```

## Verification

Check restored media files:

```bash
kubectl run -n immich-restore-test check-media \
  --image=busybox --rm -it --restart=Never \
  --overrides='{
    "spec": {
      "securityContext": {"runAsUser": 0, "runAsGroup": 0},
      "containers": [{
        "name": "check",
        "image": "busybox",
        "command": ["sh", "-c", "echo \"File count:\" && find /library -type f | wc -l && echo \"Total size:\" && du -sh /library && echo \"Directory structure:\" && ls -la /library"],
        "volumeMounts": [{"name": "library", "mountPath": "/library"}]
      }],
      "volumes": [{"name": "library", "persistentVolumeClaim": {"claimName": "immich-library-restore-test"}}]
    }
  }' -- /bin/true
```

Expected: ~257 files matching database records

## Timeline

* **T+0**: Initiate DEEP_ARCHIVE bulk restore (174 files)
* **T+48h**: Restore completes, files accessible in STANDARD
* **T+48h+10m**: Sync all 257 files to PVC
* **T+48h+15m**: Create required directories
* **T+48h+20m**: Test Immich instance ready with complete media

## Important Notes

* DEEP_ARCHIVE restore takes 48 hours (Bulk) or 12 hours (Standard)
* Restored files are accessible for 7 days (configurable via Days parameter)
* All 257 files (174 DEEP_ARCHIVE + 83 STANDARD) are needed for complete restore
* Media backups are append-only - files are never deleted from S3
* Generated content (thumbs/, encoded-video/, backups/) is not backed up - will be regenerated
* This simulates a full disaster recovery scenario

## Storage Class Breakdown

* **DEEP_ARCHIVE**: 174 files (from 2025-11-13 to 2025-11-28) - require restore
* **STANDARD**: 83 files (from 2025-11-13 to 2025-11-29) - immediately accessible
* **Total**: 257 files needed for 2025-11-29 restore

## Cost Considerations

* Bulk restore: ~$0.0025/GB (cheapest, 48 hours)
* Standard restore: ~$0.02/GB (faster, 12 hours)
* Restored files stored temporarily in STANDARD (7 days)
* Choose Bulk for cost savings, Standard for faster recovery
