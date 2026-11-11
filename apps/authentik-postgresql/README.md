# Authentik PostgreSQL

This app owns the protected CNPG database used by Authentik. Use
`make check APP=authentik-postgresql` for its configuration checks and
`make diff APP=authentik-postgresql` for a read-only comparison. Merge changes
to `main`; the Argo root owns delivery. Preserve the cluster identity, recovery
credentials, backups, and database claim during changes.

Three instances are required on separate nodes. Commits wait for one synchronous
standby, allowing a single-node outage with brief reconnection during failover.
Two unavailable nodes can block writes. Preserve the existing cluster and claims;
do not reduce the instance count without reviewing the synchronous write policy.
