# Accounts API

This synthetic internal API represents account-summary traffic owned by the
accounts tenant. Kong exposes it at `/accounts/v1` on the internal gateway.

| File | Purpose |
| --- | --- |
| [`openapi.yaml`](openapi.yaml) | API contract |
| [`default.conf`](default.conf) | Fixed demo response served by Nginx |
| [`deployment.yaml`](deployment.yaml), [`service.yaml`](service.yaml) | Workload and stable upstream address |
| [`httproute-internal.yaml`](httproute-internal.yaml) | Internal Kong route |
| [`networkpolicy-allow-kong.yaml`](networkpolicy-allow-kong.yaml) | Allows upstream traffic from Kong only |
| [`kustomization.yaml`](kustomization.yaml) | Package entry point |

Shared ownership and policy metadata lives in
[`../api-catalog.yaml`](../api-catalog.yaml).
