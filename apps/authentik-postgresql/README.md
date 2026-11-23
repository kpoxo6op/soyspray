# Authentik PostgreSQL

This app owns the protected CNPG database used by Authentik. Use
`make check APP=authentik-postgresql` for its configuration checks and
`make diff APP=authentik-postgresql` for a read-only comparison. Merge changes
to `main`; the Argo root owns delivery. Preserve the cluster identity, recovery
credentials, backups, and database claim during changes.

Three instances run on separate nodes. Commits wait for one synchronous standby
while one is streaming (`dataDurability: preferred`); when no standby is
available the primary keeps accepting writes instead of blocking. That trade
was made after 2026-11-20, when both standbys diverged and `required` blocked
every Authentik write for three days. `CNPGPrimaryWithoutStandby` pages when the
primary runs alone; rebuild a diverged standby with
`playbooks/operations/recovery/rebuild-cnpg-replica.yml`. Preserve the existing
cluster and claims.
