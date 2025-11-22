# Obsidian Offsite Backup

Daily backup of Obsidian LiveSync CouchDB data to AWS S3.

## Overview

- CronJob runs daily at 03:00 UTC
- Backs up all user databases (excludes system databases starting with `_`)
- Compresses backups with gzip
- Uploads to S3 with date-based paths: `s3://bucket/obsidian-livesync/YYYYMMDD-HHMMSS/`

## Components

- ServiceAccount: `obsidian-offsite-backup`
- ConfigMap: Backup script using Python and AWS CLI
- CronJob: Scheduled backup job
- Secret: `obsidian-offsite-writer` (AWS credentials and bucket info)

## Validation

```bash
# Check CronJob status
kubectl get cronjob -n obsidian obsidian-couchdb-offsite-backup

# Check recent backup jobs
kubectl get jobs -n obsidian -l job-name=obsidian-couchdb-offsite-backup

# View backup job logs
kubectl logs -n obsidian job/obsidian-couchdb-offsite-backup-<timestamp>

# List backups in S3
aws s3 ls s3://obsidian-offsite-archive-au2/obsidian-livesync/ --recursive
```

