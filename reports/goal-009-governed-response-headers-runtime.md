# Goal009 Governed Response Headers Runtime Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T10:16:51+12:00

Kubernetes context: kubernetes-admin@cluster.local

Credential source: environment variables

## Runtime smoke
server dry-run before apply: pass
positive governed response header smoke: pass; status=200
header X-Content-Type-Options=nosniff: pass
header X-Frame-Options=DENY: pass
header Referrer-Policy=no-referrer: pass
header X-BankLab-Response-Policy=goal009: pass
accounts marker preservation: pass; marker=banklab-accounts-ok
goal004 correlation ID preservation: pass
goal004 rate-limit header preservation: pass
missing API key remains unauthorized: pass; status=401
wrong ACL key remains forbidden: pass; status=403
runtime route annotation includes goal009 plugin: pass
goal009 KongPlugin resource exists: pass
