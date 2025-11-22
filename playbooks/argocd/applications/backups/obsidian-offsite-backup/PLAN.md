# Obsidian Offsite Backup Plan

## Overview
Daily backup of Obsidian LiveSync CouchDB data to AWS S3.

## Components

1. **CronJob**
   - Schedule: Daily (e.g., 03:00 UTC)
   - Image: `amazon/aws-cli` (plus `curl` and `jq` installed via script or custom image)
   - Resources: Minimal (CPU: 100m, Mem: 256Mi)

2. **Backup Script** (ConfigMap)
   - Connect to CouchDB service
   - Iterate through all databases (`_all_dbs`)
   - For each database:
     - Dump content to JSON/LD file
     - Gzip compression
     - Upload to `s3://$BUCKET_NAME/obsidian-livesync/$DATE/`
   - Prune old backups (S3 Lifecycle or script)

3. **Secrets**
   - `obsidian-offsite-writer` (AWS Credentials & Bucket info)
   - `obsidian-livesync-couchdb` (CouchDB Admin Creds - existing)

## Implementation Steps

1. [ ] Create `obsidian-offsite-writer` secret (add to Ansible playbooks)
2. [ ] Create `ConfigMap` with backup script (`backup-couchdb.sh`)
3. [ ] Create `CronJob` manifest
4. [ ] Add ArgoCD Application definition
5. [ ] Test backup and restore procedure

## Restore Procedure (Draft)
1. Download backup file from S3
2. Unzip
3. Use `curl` / `couchrestore` to push documents back to a fresh CouchDB instance

