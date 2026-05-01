# 2026-05-01 Obsidian LiveSync Storage Recovery

## Summary

Obsidian LiveSync returned HTTP 503 because the CouchDB pod had no ready
endpoint. The pod could not mount its Longhorn PVC after the node storage
device backing `/storage` remounted read-only.

The server was recovered temporarily by restoring the latest S3 CouchDB backup
into a rescue CouchDB deployment backed by node root-disk hostPath storage:

- rescue path: `/var/lib/obsidian-rescue-couchdb-data`
- restored backup object:
  `s3://obsidian-offsite-archive-au2/obsidian-livesync/20260501-005503/obsidian-main-20260501-005503.json`
- restored database: `obsidian-main`
- restored document count: `14878`

The original Longhorn PVC was not deleted:

- PVC: `database-storage-obsidian-livesync-couchdb-0`
- Longhorn volume: `pvc-87a2e7b1-6011-4580-8dce-e9433a6f0900`
- last known state after recovery: detached/unknown

## Live Drift Left Intentionally

The following Argo applications were paused to avoid self-heal undoing the
rescue state while Longhorn storage is repaired:

- `longhorn`
- `obsidian-livesync`

The live Obsidian service selectors still point at labels
`app=couchdb,release=obsidian-livesync`; the rescue deployment uses those
labels so the existing ingress and service names continue to work.

## Important Follow-Up

Do not delete the original Longhorn Obsidian PVC until the phone and laptop
vaults have fully synced against the rescue CouchDB and the S3 backup has been
verified. The S3 restore point is from `2026-05-01 00:55:03 UTC`, so edits made
after that time may only exist on client devices.

After Longhorn is stable again, migrate the rescue database back to a normal
declarative CouchDB deployment/PVC, then re-enable Argo self-heal.
