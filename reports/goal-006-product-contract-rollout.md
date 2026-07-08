# Goal006 Product Contract Rollout Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T01:20:18+12:00

Kubernetes context: kubernetes-admin@cluster.local

Product ID: accounts-self-service-health-v1

Tenant: retail-accounts

API: accounts

Route/service affected: tenant-accounts/HTTPRoute/banklab-accounts

Plugin applied: tenant-accounts/KongPlugin/goal006-product-contract-header

Credential source: environment variables

## Apply output
kongplugin.configuration.konghq.com/goal006-product-contract-header created
httproute.gateway.networking.k8s.io/banklab-accounts configured

## Runtime smoke
positive product smoke: pass; status=200; product_header=accounts-self-service-health-v1
accounts marker preservation: pass; marker=banklab-accounts-ok
goal004 correlation ID preservation: pass
goal004 rate-limit header preservation: pass
missing API key remains unauthorized: pass; status=401
wrong ACL key remains forbidden: pass; status=403
runtime route annotation includes goal006 plugin: pass
