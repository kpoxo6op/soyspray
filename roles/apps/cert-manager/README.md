# Certificate bootstrap during migration

This role retains the existing Cloudflare-token and shared public Bitnami OCI
repository Secret bootstrap. It no longer submits an Argo Application. Use the
[native certificate app](../../../apps/cert-manager-config/README.md) for deployment,
status, checks, and lifecycle protection. Keep these remaining bootstrap actions
until their replacements are verified.
