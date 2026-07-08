# Goal005 Change Rollout Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T00:29:00+12:00

Kubernetes context: kubernetes-admin@cluster.local

Sample change ID: goal-005-normal-change

Tenant: retail-accounts

API: accounts

Route/service affected: tenant-accounts/HTTPRoute/banklab-accounts

Manifest applied: scripts/render_goal005_change.py

## Apply output
kongplugin.configuration.konghq.com/goal005-normal-change-header created
httproute.gateway.networking.k8s.io/banklab-accounts configured

## Runtime smoke
HTTP smoke result: pass; status=200
observed temporary header: pass; X-Goal005-Change-Id=goal-005-normal-change
goal004 marker/header preservation: pass; marker=banklab-accounts-ok; correlation-id=present
auth preservation: pass; valid API key accepted
rate-limit header preservation: pass
