# Authentik PostgreSQL

This app owns the protected CNPG database used by Authentik. Use
`make check APP=authentik-postgresql` for its configuration checks and
`make diff APP=authentik-postgresql` for a read-only comparison. Merge changes
to `main`; the Argo root owns delivery. Preserve the cluster identity, recovery
credentials, backups, and database claim during changes.
