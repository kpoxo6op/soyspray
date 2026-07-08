# Goal006 Product Contract Rollback Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T01:20:36+12:00

Kubernetes context: kubernetes-admin@cluster.local

Rollback command: make goal006-product-contract-rollback-and-smoke

Resources removed or reverted: KongPlugin/tenant-accounts/goal006-product-contract-header removed; HTTPRoute/tenant-accounts/banklab-accounts restored to stable goal005 annotation set.

Credential source: environment variables

## Rollback output
httproute.gateway.networking.k8s.io/banklab-accounts configured
kongplugin.configuration.konghq.com "goal006-product-contract-header" deleted from tenant-accounts namespace

## Runtime smoke after rollback
product contract header absence: pass
accounts marker preservation after rollback: pass; marker=banklab-accounts-ok
goal004 correlation ID preservation after rollback: pass
goal004 rate-limit header preservation after rollback: pass
missing API key remains unauthorized after rollback: pass; status=401
wrong ACL key remains forbidden after rollback: pass; status=403
runtime route annotation omits goal006 plugin after rollback: pass
