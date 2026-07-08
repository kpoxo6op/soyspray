# Goal004 Rate Limit Results

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-08T23:14:08+12:00

Kubernetes context: kubernetes-admin@cluster.local

Rate limit policy: redis

## Checks
accounts rate-limit burst: pass; statuses=200 200 200 429 429 429 429 429 429 429 429 429 429 429 429 429 429 429 429 429
redis policy evidence: pass; plugin config is validated locally and runtime returned 429
