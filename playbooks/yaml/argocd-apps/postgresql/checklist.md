# Immich PostgreSQL Prerequisites Checklist

## PostgreSQL Version Requirements

- [x] PostgreSQL version 14, 15, or 16 installed

## pgvecto.rs Setup

- [x] pgvecto.rs extension installed
- [x] pgvecto.rs version >= 0.2.0, < 0.4.0
- [x] shared_preload_libraries includes 'vectors.so' in postgresql.conf

## Database Configuration

- [x] Database created for Immich
- [x] Database ownership assigned to Immich user

## Required Extensions

- [x] vectors extension created

  ```sh
  kubectl -n postgresql exec -it postgresql-0 -- psql -U immich -c "SELECT * FROM pg_extension WHERE extname = 'vectors';"
  ```

- [x] earthdistance extension created (including cube)

  ```sh
  kubectl -n postgresql exec -it postgresql-0 -- psql -U immich -c "SELECT * FROM pg_extension WHERE extname IN ('earthdistance', 'cube');"
  ```

## Permissions and Schema Setup

- [x] Search path set to "$user", public, vectors
- [x] vectors schema ownership assigned to Immich user

  ```sh
  kubectl -n postgresql exec -it postgresql-0 -- psql -U immich -c "SELECT n.nspname AS schema, pg_catalog.pg_get_userbyid(n.nspowner) AS owner FROM pg_catalog.pg_namespace n WHERE n.nspname = 'vectors';"
  ```

- [x] SELECT permission granted on pg_vector_index_stat

  ```sh
  kubectl -n postgresql exec -it postgresql-0 -- psql -U immich -c "SELECT has_table_privilege('immich', 'pg_vector_index_stat', 'SELECT');"
  ```

## User Permissions (Choose One)

- [x] Superuser permissions granted to Immich user (recommended for automated backups)

## Connection Setup

- [x] Database connection URL configured correctly
