# Goal004 Security Negative Test Results

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T02:13:09+12:00

Kubernetes context: kubernetes-admin@cluster.local

Credential source: local environment variables

## Negative checks
missing API key returns 401: pass; status=401
invalid API key returns 401: pass; status=401
valid API key for wrong ACL group returns 403: pass; status=403
missing JWT returns 401: pass; status=401
invalid JWT signature returns 401: pass; status=401
expired JWT returns 401: pass; status=401
internal API unavailable through external hostname: pass; status=404
unknown host remains 404: pass; status=404
unknown path remains 404: pass; status=404
admin API negative probe: pass
