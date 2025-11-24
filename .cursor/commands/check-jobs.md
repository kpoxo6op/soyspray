# Check Jobs

## Overview

Check last execution time and status of backup jobs, and verify recent S3 backup files with storage classes.

## Database Backup Job Status

### Check Last Execution Time and Status
```bash
kubectl get scheduledbackup -n postgresql -o custom-columns=NAME:.metadata.name,LAST_BACKUP:.status.lastBackup,CLUSTER:.spec.cluster.name
```

## Media Backup Job Status

### Check Last Execution Time and Status
```bash
kubectl get cronjob -n immich immich-media-offsite-sync -o jsonpath='{range .status}{.lastScheduleTime}{"\n"}{.lastSuccessfulTime}{"\n"}{end}' && echo ""
kubectl get jobs -n immich -l app=immich-offsite-backup --sort-by=.metadata.creationTimestamp -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,COMPLETION_TIME:.status.completionTime | tail -3
```

## Obsidian Backup Job Status

### Check Last Execution Time and Status
```bash
kubectl get cronjob -n obsidian obsidian-couchdb-offsite-backup -o jsonpath='{range .status}{.lastScheduleTime}{"\n"}{.lastSuccessfulTime}{"\n"}{end}' && echo ""
kubectl get jobs -n obsidian -l job-name --sort-by=.metadata.creationTimestamp -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,COMPLETION_TIME:.status.completionTime | tail -3
```

## AWS S3 Backup Files

### Check Last Database Backup Files and Storage Class
```bash
BUCKET="${BUCKET_NAME:-immich-offsite-archive-au2}"
echo "=== Last 5 Database Backup Files ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "immich/db/" --query 'sort_by(Contents, &LastModified)[-5:].[Key,StorageClass,LastModified,Size]' --output table
```

### Check Last Media Backup Files and Storage Class
```bash
BUCKET="${BUCKET_NAME:-immich-offsite-archive-au2}"
echo "=== Last 5 Media Backup Files ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "immich/media/" --query 'sort_by(Contents, &LastModified)[-5:].[Key,StorageClass,LastModified,Size]' --output table
```

### Check Last Obsidian Backup Files and Storage Class
```bash
BUCKET="${OBSIDIAN_BUCKET_NAME:-obsidian-offsite-archive-au2}"
echo "=== Last 5 Obsidian Backup Files ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "obsidian-livesync/" --query 'sort_by(Contents, &LastModified)[-5:].[Key,StorageClass,LastModified,Size]' --output table
```

### Check Storage Class Distribution
```bash
BUCKET="${BUCKET_NAME:-immich-offsite-archive-au2}"
echo "=== Database Backup Storage Classes ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "immich/db/" --query 'Contents[].StorageClass' --output text 2>/dev/null | tr '\t' '\n' | sort | uniq -c
echo -e "\n=== Media Backup Storage Classes ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "immich/media/" --query 'Contents[].StorageClass' --output text 2>/dev/null | tr '\t' '\n' | sort | uniq -c
BUCKET="${OBSIDIAN_BUCKET_NAME:-obsidian-offsite-archive-au2}"
echo -e "\n=== Obsidian Backup Storage Classes ==="
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "obsidian-livesync/" --query 'Contents[].StorageClass' --output text 2>/dev/null | tr '\t' '\n' | sort | uniq -c
```

## Quick Status Summary
```bash
echo "=== BACKUP JOBS STATUS ==="
echo "Database Backup:"
kubectl get scheduledbackup -n postgresql -o custom-columns=NAME:.metadata.name,LAST_BACKUP:.status.lastBackup
echo -e "\nMedia Backup:"
kubectl get cronjob -n immich immich-media-offsite-sync -o jsonpath='Last Schedule: {.status.lastScheduleTime}{"\n"}Last Success: {.status.lastSuccessfulTime}{"\n"}'
echo -e "\nRecent Media Jobs:"
kubectl get jobs -n immich -l app=immich-offsite-backup --sort-by=.metadata.creationTimestamp -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,COMPLETION:.status.completionTime | tail -3
echo -e "\nObsidian Backup:"
kubectl get cronjob -n obsidian obsidian-couchdb-offsite-backup -o jsonpath='Last Schedule: {.status.lastScheduleTime}{"\n"}Last Success: {.status.lastSuccessfulTime}{"\n"}'
echo -e "\nRecent Obsidian Jobs:"
kubectl get jobs -n obsidian -l job-name --sort-by=.metadata.creationTimestamp -o custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,COMPLETION:.status.completionTime | tail -3
echo -e "\n=== S3 LAST FILES ==="
BUCKET="${BUCKET_NAME:-immich-offsite-archive-au2}"
echo "Database (last 3):"
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "immich/db/" --query 'sort_by(Contents, &LastModified)[-3:].[Key,StorageClass,LastModified]' --output table 2>/dev/null || echo "Unable to check"
echo -e "\nMedia (last 3):"
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "immich/media/" --query 'sort_by(Contents, &LastModified)[-3:].[Key,StorageClass,LastModified]' --output table 2>/dev/null || echo "Unable to check"
BUCKET="${OBSIDIAN_BUCKET_NAME:-obsidian-offsite-archive-au2}"
echo -e "\nObsidian (last 3):"
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "obsidian-livesync/" --query 'sort_by(Contents, &LastModified)[-3:].[Key,StorageClass,LastModified]' --output table 2>/dev/null || echo "Unable to check"
```
