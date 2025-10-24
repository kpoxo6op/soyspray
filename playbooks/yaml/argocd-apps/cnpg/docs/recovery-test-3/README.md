# Recovery Drill 3

## Previous Drill Summary

Test 2 recovered cluster from backup 20251024T074758 to target 08:35:00 UTC. Encountered timezone conversion error (NZDT vs UTC). Successfully recovered 99 assets, verified extensions, manually restored media from S3, created missing folders. Cluster now runs on Timeline 2 with continuous archiving active.

## Next Drill

1. Pick new recovery point from Timeline 2 backups in S3
2. Update targetTime in immich-db-cluster.yaml to new timestamp
3. Delete immich app then cluster via ArgoCD
4. Apply ansible playbook to trigger recovery
5. Monitor recovery logs for PITR completion
6. Verify database connectivity and asset count
7. Restore media from S3 if needed
8. Test Immich web UI access

Focus: Test recovery from Timeline 2 (post-promotion) backups.
