# CNPG operator + Immich DB A/B clusters (PostgreSQL 16 + pgvecto.rs v0.3.0)

This app installs the CloudNativePG operator and provisions **A/B PostgreSQL 16 clusters** with **pgvecto.rs `vectors` v0.3.0** for disaster recovery. Each cluster creates the `immich` database and role, installs `cube`, `earthdistance`, and `vectors`, sets `search_path`, and assigns schema/grants. An alias service (`immich-db-active`) provides stable connectivity while enabling A↔B switchover testing.

## Deploy order

1. Sync `cnpg-operator` (namespace `cnpg-system`).
2. Sync `immich-db-active` (namespace `postgresql`).

### For Production Use
3. Sync `immich-db-a` (namespace `postgresql`) - starts with cluster A as active.

### For Disaster Recovery Testing
Use the procedures in `docs/recovery-exercise-1/README.md` which create clusters via restore from S3 backup, not the prod apps directly.

## Connection for Immich

**Stable alias service** (read/write): `immich-db-active.postgresql.svc.cluster.local:5432`
Database URL: `postgresql://immich:immich@immich-db-active.postgresql.svc.cluster.local/immich`

The alias points to either `immich-db-a-rw` or `immich-db-b-rw` depending on which cluster is active during A↔B switchover testing.

## What's included

- Postgres **16**, pgvecto.rs **0.3.0** (extension name **vectors**)
- Longhorn **20Gi** PVC, namespace **postgresql**
- Bootstrap SQL:
  - `CREATE EXTENSION cube, earthdistance, "vectors"`
  - `ALTER DATABASE immich SET search_path TO "$user", public, vectors`
  - `ALTER SCHEMA vectors OWNER TO immich`
  - `GRANT SELECT ON pg_vector_index_stat TO immich`
- `shared_preload_libraries = vectors`

## Validation Commands

After deployment, verify the database configuration using these commands:

### 1. Check PostgreSQL Version
```bash
# Find the active cluster pod (either immich-db-a or immich-db-b)
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster -o name | grep -E "(immich-db-a|immich-db-b)" | head -n1 | sed 's#pod/##')
kubectl -n postgresql exec "$POD" -- psql -h localhost -U immich -d immich -c "SELECT version();"
```

### 2. Verify Extensions Installation
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT extname FROM pg_extension WHERE extname IN ('vectors','cube','earthdistance') ORDER BY 1;\""
```

### 3. Check Search Path Configuration
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SHOW search_path;\""
```

### 4. Verify Schema Ownership
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT schemaname, owner FROM (SELECT schemaname, pg_get_userbyid(owner) as owner FROM (SELECT nspname as schemaname, nspowner as owner FROM pg_namespace WHERE nspname = 'vectors') subq) subq2;\""
```

### 5. Check Permissions
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT has_table_privilege('immich', 'pg_vector_index_stat', 'SELECT');\""
```

### 6. Test Vector Operations
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT '[1,2,3]'::vector AS test_vector;\""
```

### 7. Test Geometric Types (Cube Extension)
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT '(1,2)'::point AS test_point;\""
```

### 8. Test Earth Distance (Earthdistance Extension)
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT earth_distance(ll_to_earth(40.0, -74.0), ll_to_earth(40.1, -74.1));\""
```

### 9. Verify Current Context
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d immich -c \"SELECT current_database(), current_user;\""
```

### 10. Check Database Existence
```bash
kubectl -n postgresql exec "$POD" -- bash -c "export PGPASSWORD=immich && psql -h localhost -U immich -d postgres -c \"SELECT datname FROM pg_database WHERE datname = 'immich';\""
```

## Architecture at a glance

```text
+---------------------+            +-------------------------------+
|  ArgoCD (argocd)    |            |  CloudNativePG Operator       |
|  - cnpg-operator    |----------->|  (Deployment in cnpg-system)  |
|  - immich-db-active |      CRDs  +-------------------------------+
|  - immich-db-a      |
|  - immich-db-b      |
+----------+----------+
           |
           | Clusters (CRs)
           v
+-------------------------------+       +-------------------------------+
|  CNPG Cluster: immich-db-a    |       |  CNPG Cluster: immich-db-b    |
|  instances: 1 (PG16)          |       |  instances: 1 (PG16)          |
|  image: CNPG + pgvecto.rs     |       |  image: CNPG + pgvecto.rs     |
|  storage: Longhorn 20Gi       |       |  storage: Longhorn 20Gi       |
|  backups: S3 (serverName:     |       |  backups: S3 (serverName:     |
|    immich-db)                 |       |    immich-db)                 |
+-------------------------------+       +-------------------------------+
           |                                       |
           v                                       v
    immich-db-a-rw (RW endpoint)         immich-db-b-rw (RW endpoint)
           |                                       |
           +---------------------------------------+
                           |
                           v
                +-------------------------------+
                |  ExternalName Service        |
                |  immich-db-active            |
                |  -> immich-db-a-rw OR        |
                |     immich-db-b-rw           |
                +-------------------------------+
```

## Disaster Recovery Features

* **A/B Switchover**: Two identical clusters with stable alias service for testing recovery procedures
* **Backups + PITR**: S3-compatible object storage with WAL archiving (serverName: immich-db)
* **Restore Testing**: Dedicated restore apps for each cluster to test S3-to-cluster recovery

## Later add

* **High availability**: `instances: 3` for HA with automated failover.
* **Pooler**: connection pooling for Immich.
* **Replica cluster**: read‑only replica or staging.
