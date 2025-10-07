# Redis

Redis is deployed as a dependency for Immich and other applications in the cluster.

## Configuration

- **Architecture:** Standalone
- **Authentication:** Disabled (uses `ALLOW_EMPTY_PASSWORD=yes`)
- **Storage:** Longhorn persistent volume (5Gi)
- **Registry:** `bitnamilegacy/redis` (Bitnami Legacy due to 2024/2025 catalog changes)

## Quick Validation

Check deployment health:

```bash
kubectl -n redis exec redis-master-0 -- redis-cli PING
```

## Services

- `redis-master.redis.svc.cluster.local` - Primary Redis service (port 6379)
