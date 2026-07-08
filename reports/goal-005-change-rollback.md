# Goal005 Change Rollback Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T00:29:15+12:00

Kubernetes context: kubernetes-admin@cluster.local

Rollback command: make goal005-change-rollback-and-smoke

Resources removed or reverted: KongPlugin/tenant-accounts/goal005-normal-change-header removed; HTTPRoute/tenant-accounts/banklab-accounts reverted to stable goal005 annotation set.

## Rollback output
httproute.gateway.networking.k8s.io/banklab-accounts configured
kongplugin.configuration.konghq.com "goal005-normal-change-header" deleted from tenant-accounts namespace

## Runtime smoke after rollback
HTTP smoke result after rollback: pass; status=200
temporary header absence: pass
goal004 marker/header behavior remains: pass; marker=banklab-accounts-ok; correlation-id=present
missing API key remains unauthorized: pass; status=401
wrong ACL key remains forbidden: pass; status=403
goal004 authentication and authorization still behave correctly: pass
