# Security Operations

Cluster security playbooks for maintenance tasks.

- `sync-certificates.yml` - Synchronize TLS certificates across namespaces
- `cleanup-stale-cert-manager-resources.yml` - Report or remove stale per-app cert-manager resources after switching wildcard-covered ingresses to the shared reflected `prod-cert-tls` secret. Defaults to report-only; apply with `-e cert_cleanup_apply=true`.
