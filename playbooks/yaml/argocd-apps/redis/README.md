# Redis

Redis is deployed as a dependency for Immich and other applications in the cluster.

## Configuration

Redis is configured with:

- Standalone architecture
- Authentication disabled
- Persistent storage using Longhorn

## Connection Testing

To test connectivity to Redis, run:

```bash
kubectl run redis-test --rm -it --restart=Never --image=redis:alpine -- sh -c "redis-cli -h redis-master.redis.svc.cluster.local ping"
```

Expected output:

```sh
PONG
pod "redis-test" deleted
```

## Related Services

The following Redis services are available:

- `redis-headless.redis.svc.cluster.local` - Headless service
- `redis-master.redis.svc.cluster.local` - Master service (used by applications)
