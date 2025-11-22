# Obsidian LiveSync with CouchDB

Self-hosted LiveSync deployment for Obsidian note synchronization using CouchDB backend.

## Configuration

Database name: `obsidian-main` (lowercase, no spaces, no special characters, cannot start with underscore). Use same name on all devices.

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
