# Goal007 Consumer Onboarding Rollout Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T01:45:08+12:00

Kubernetes context: kubernetes-admin@cluster.local

Consumer: branch-insights-app

Owning team: branch-insights

Target product: accounts-self-service-health-v1

Target route: tenant-accounts/HTTPRoute/banklab-accounts

Expected baseline plugins: banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id

Credential source: environment variable

Credential values printed: no

## Apply output
secret/banklab-branch-insights-app-key-auth created
secret/banklab-branch-insights-app-accounts-acl created
kongconsumer.configuration.konghq.com/branch-insights-app created

## Runtime smoke
onboarded consumer positive smoke: pass; status=200; consumer=branch-insights-app; marker=banklab-accounts-ok
goal004 correlation ID preservation: pass
goal004 rate-limit header preservation: pass
goal006 product marker remains absent: pass
missing API key remains unauthorized: pass; status=401
valid key without accounts ACL remains forbidden: pass; status=403
onboarded consumer rate-limit burst: pass; statuses=200 200 200 429 429 429 429 429 429 429 429 429 429 429 429 429 429 429 429 429
runtime consumer and credential resources exist: pass
runtime route annotation preserves baseline plugins: pass; plugins=banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id
