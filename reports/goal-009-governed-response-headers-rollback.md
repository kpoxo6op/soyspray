# Goal009 Governed Response Headers Rollback Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T10:17:06+12:00

Kubernetes context: kubernetes-admin@cluster.local

Rollback command: make rollback-goal-009

Resources removed or reverted: KongPlugin/tenant-accounts/banklab-goal009-security-headers removed; HTTPRoute/tenant-accounts/banklab-accounts restored to stable goal005 annotation set.

Credential source: environment variables

## Rollback output
httproute.gateway.networking.k8s.io/banklab-accounts configured
kongplugin.configuration.konghq.com "banklab-goal009-security-headers" deleted from tenant-accounts namespace

## Runtime smoke after rollback
goal009 response headers absent after rollback: pass
accounts marker preservation after rollback: pass; marker=banklab-accounts-ok
goal004 correlation ID preservation after rollback: pass
goal004 rate-limit header preservation after rollback: pass
missing API key remains unauthorized after rollback: pass; status=401
wrong ACL key remains forbidden after rollback: pass; status=403
runtime route annotation omits goal009 plugin after rollback: pass
goal009 KongPlugin resource absent after rollback: pass
