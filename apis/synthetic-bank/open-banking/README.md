# Open Banking API

This synthetic partner API demonstrates an externally exposed route. Kong
serves `/open-banking/v1` through the external gateway and applies the policy
profile recorded in the API catalog.

| File | Purpose |
| --- | --- |
| [`openapi.yaml`](openapi.yaml) | API contract |
| [`default.conf`](default.conf) | Fixed demo response served by Nginx |
| [`deployment.yaml`](deployment.yaml), [`service.yaml`](service.yaml) | Workload and stable upstream address |
| [`httproute-external.yaml`](httproute-external.yaml) | External Kong route |
| [`networkpolicy-allow-kong.yaml`](networkpolicy-allow-kong.yaml) | Allows upstream traffic from Kong only |
| [`kustomization.yaml`](kustomization.yaml) | Package entry point |

Shared ownership and policy metadata lives in
[`../api-catalog.yaml`](../api-catalog.yaml).
