# Goal007 Consumer Onboarding Rollback

Use this runbook when the `branch-insights-app` consumer onboarding path must be
removed after rollout.

## Scope

Rollback removes only:

- `synthetic-clients/KongConsumer/branch-insights-app`
- `synthetic-clients/Secret/banklab-branch-insights-app-key-auth`
- `synthetic-clients/Secret/banklab-branch-insights-app-accounts-acl`

Rollback must preserve:

- `tenant-accounts/HTTPRoute/banklab-accounts`
- `banklab-key-auth`
- `banklab-acl`
- `banklab-rate-limit`
- `banklab-correlation-id`
- all goal004, goal005, and post-goal006-rollback runtime resources

## Guard

Before rollback, set:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local
```

Verify the active context:

```bash
kubectl config current-context
```

It must match `BANKLAB_TARGET_CONTEXT`.

## Rollback

```bash
make goal007-consumer-onboarding-rollback-and-smoke
```

## Acceptance

Rollback is accepted only when:

- the `branch-insights-app` `KongConsumer` is absent
- both runtime credential Secrets are absent
- the removed consumer key is rejected with `401` when the key is available in
  the shell environment
- the baseline mobile-banking accounts consumer still receives `200`
- missing credentials still receive `401`
- a valid key without the accounts ACL still receives `403`
- correlation ID and rate-limit headers remain present
- `tenant-accounts/HTTPRoute/banklab-accounts` keeps the stable plugin
  annotation `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`
- Kong Admin API safety checks remain passing through the goal007 runtime-ready
  sequence

Evidence is written to `reports/goal-007-consumer-onboarding-rollback.md`.
