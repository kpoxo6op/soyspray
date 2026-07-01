# Obsidian LiveSync with CouchDB

Self-hosted LiveSync deployment for Obsidian note synchronization using CouchDB backend.

## Configuration

Database name: `obsidian-main` (lowercase, no spaces, no special characters, cannot start with underscore). Use same name on all devices.

## Storage State

The active CouchDB pod is `obsidian-livesync-couchdb-hostpath-rescue`, but it no
longer uses hostPath storage. It mounts the Longhorn PVC
`obsidian-livesync-couchdb-rescue-longhorn`.

The older StatefulSet PVC `database-storage-obsidian-livesync-couchdb-0` is kept
only as rollback data from the May 2026 storage incident. Do not delete it until
the active Longhorn rescue PVC, the offsite backup, and the document count have
all been checked after this app is synced.

## Validation

```bash
# Get credentials from secret and test authenticated connection
USER=$(kubectl get secret obsidian-livesync-couchdb -n obsidian -o jsonpath='{.data.adminUsername}' | base64 -d)
PASS=$(kubectl get secret obsidian-livesync-couchdb -n obsidian -o jsonpath='{.data.adminPassword}' | base64 -d)

# List all databases
curl -u $USER:$PASS https://obsidian.soyspray.vip/_all_dbs

# Check database contents
curl -u $USER:$PASS https://obsidian.soyspray.vip/obsidian-main/_all_docs | jq '.total_rows'

# List only note files (excludes metadata)
curl -u $USER:$PASS "https://obsidian.soyspray.vip/obsidian-main/_all_docs?descending=true&include_docs=true" | jq '.rows[] | select(.doc.type == "plain") | .doc.path'
```

## Retiring the old PVC

After the PR is merged and Argo shows `obsidian-livesync` as synced, verify the
current service before removing the old volume:

```bash
kubectl -n obsidian get pods,endpoints,pvc
curl -u $USER:$PASS https://obsidian.soyspray.vip/_up
curl -u $USER:$PASS https://obsidian.soyspray.vip/obsidian-main/_all_docs | jq '.total_rows'
aws s3 ls s3://obsidian-offsite-archive-au2/obsidian-livesync/ --recursive | tail
```

Only then remove the rollback PVC:

```bash
kubectl -n obsidian delete pvc database-storage-obsidian-livesync-couchdb-0
```
