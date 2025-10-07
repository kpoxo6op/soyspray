# Immich v2.0.1 - Photo Management

## Quick Health Check

```bash
# Check pod status
kubectl get pods -n immich

# API health check
curl -k https://immich.soyspray.vip/api/server/ping
# Expected: {"res":"pong"}

# Version check
curl -k https://immich.soyspray.vip/api/server/version
# Expected: {"major":2,"minor":0,"patch":1}
```

## Access

- **Web UI**: <https://immich.soyspray.vip>
- **LoadBalancer IP**: 192.168.50.208:2283
- **Internal Service**: immich-server.immich.svc.cluster.local:2283

## Configuration

### Database

- **Type**: CNPG PostgreSQL 16
- **Service**: immich-db-rw.postgresql.svc.cluster.local:5432
- **Vector Extension**: pgvecto.rs v0.3.0
- **Database**: immich

### Redis

- **Service**: redis-master.redis.svc.cluster.local:6379
- **Type**: Bitnami Redis (standalone, no auth)

### Storage

- **PVC**: immich-library (Longhorn, 100Gi)
- **StorageClass**: longhorn

### Features

- ✅ Smart Search
- ✅ Facial Recognition
- ✅ Duplicate Detection
- ✅ Map functionality
- ✅ Reverse Geocoding
- ❌ Machine Learning (disabled)

## Troubleshooting

### Check Logs

```bash
kubectl logs -f deployment/immich-server -n immich
```

### Database Connection

```bash
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db -o name | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"
```

### Internal Connectivity Test

```bash
kubectl -n immich run curltest --rm -it --image=curlimages/curl --restart=Never -- \
  curl -v http://immich-server.immich.svc.cluster.local:2283/api/server/ping
```

Expected: `{"res":"pong"}`
