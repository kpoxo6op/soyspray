# CNPG operator + Immich DB cluster (PostgreSQL 16 + pgvecto.rs v0.3.0)

This app installs the CloudNativePG operator and provisions a single‑instance **PostgreSQL 16** cluster with **pgvecto.rs `vectors` v0.3.0**. It creates the `immich` database and role, installs `cube`, `earthdistance`, and `vectors`, sets `search_path`, and assigns schema/grants to match the current setup.

## Deploy order

1. Sync `cnpg-operator` (namespace `cnpg-system`).
2. Sync `immich-db` (namespace `postgresql`).

## Connection for Immich

Service DNS (read/write): `immich-db-rw.postgresql.svc.cluster.local:5432`
Database URL: `postgresql://immich:immich@immich-db-rw.postgresql.svc.cluster.local/immich`

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
POD=$(kubectl -n postgresql get pod -l cnpg.io/cluster=immich-db -o name | head -n1 | sed 's#pod/##')
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
|  - immich-db        |      CRDs  +-------------------------------+
+----------+----------+
           |
           | Cluster (CR)
           v
+-------------------------------+       Kubernetes Services
|  CNPG Cluster: immich-db      |       ----------------------------
|  instances: 1 (PG16)          |   -->  immich-db-rw (RW endpoint)
|  image: CNPG + pgvecto.rs     |   -->  immich-db-ro (RO endpoint)
|  storage: Longhorn 20Gi       |
|  bootstrap: initdb + SQL      |
+-------------------------------+
```

## Later add

* **High availability**: `instances: 3` for HA with automated failover.
* **Backups + PITR**: object storage (S3‑compatible) with WAL archiving.
* **Pooler**: connection pooling for Immich.
* **Replica cluster**: read‑only replica or staging.
