# Goal007 Consumer Onboarding Rollback Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T01:45:15+12:00

Kubernetes context: kubernetes-admin@cluster.local

Rollback command: make goal007-consumer-onboarding-rollback-and-smoke

Resources removed: KongConsumer/synthetic-clients/branch-insights-app, Secret/synthetic-clients/banklab-branch-insights-app-key-auth, Secret/synthetic-clients/banklab-branch-insights-app-accounts-acl

Resources preserved: tenant-accounts/HTTPRoute/banklab-accounts and baseline plugins banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id

Credential source: environment variables

Credential values printed: no

## Rollback output
kongconsumer.configuration.konghq.com "branch-insights-app" deleted from synthetic-clients namespace
secret "banklab-branch-insights-app-key-auth" deleted from synthetic-clients namespace
secret "banklab-branch-insights-app-accounts-acl" deleted from synthetic-clients namespace

## Runtime smoke after rollback
consumer and runtime credential resources removed: pass
removed consumer key rejected after rollback: pass; status=401
baseline accounts consumer still succeeds after rollback: pass; status=200
correlation ID and rate-limit headers preserved after rollback: pass
goal006 product marker remains absent after rollback: pass
missing API key remains unauthorized after rollback: pass; status=401
wrong ACL key remains forbidden after rollback: pass; status=403
runtime route annotation matches post-rollback baseline: pass; plugins=banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id
