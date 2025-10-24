# Recovery Drill 3

## Previous Drill Summary

Test 2 recovered cluster from backup 20251024T074758 to target 08:35:00 UTC.
Encountered timezone conversion error (NZDT vs UTC). Successfully recovered 99
assets, verified extensions, manually restored media from S3, created missing
folders. Cluster now runs on Timeline 2 with continuous archiving active.

## New Approach - Blue/Green DB Swap

No deletes. Zero downtime. Same manifests for drills and disasters.

Pattern: DNS alias Service (immich-db-active) points to current primary. Recovery creates new cluster (immich-db-restore). Flip alias externalName to cutover. Immich always uses alias, never edited.

## Implementation (Next Branch)

1. Create Service/immich-db-active (ExternalName → immich-db-rw)
2. Create immich-db-restore app with recovery bootstrap
3. Update Immich DB_URL to use immich-db-active alias
4. Add targetTime overlay for drill-specific recovery points

## Drill Steps

1. Update targetTime in immich-db-restore overlay
2. Sync immich-db-restore app, monitor PITR
3. Verify recovered cluster
4. Flip alias to immich-db-restore-rw (optional test)
5. Cleanup: Flip back, delete restore cluster

Real disaster: Same steps but enable backups on restore cluster after cutover.

Focus: Eliminate delete/recreate risk. Match real recovery exactly.
