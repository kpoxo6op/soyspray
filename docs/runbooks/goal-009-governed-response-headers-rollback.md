# Goal009 Governed Response Headers Rollback

Use this runbook to remove the Goal009 response-header plugin from the
accounts API path.

## Preconditions

- Confirm the current Kubernetes context is the approved lab context.
- Confirm the branch source has been pushed before runtime mutation.
- Set the mutation guard variables for the exact command being run.

## Rollback

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true \
BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local \
make rollback-goal-009
```

The target reapplies the stable accounts route annotation, deletes
`tenant-accounts/KongPlugin/banklab-goal009-security-headers`, and runs the
post-rollback smoke checks for the accounts path.

## Verification

The rollback report is written to:

- `reports/goal-009-governed-response-headers-rollback.md`

Expected pass conditions:

- `X-BankLab-Response-Policy` is absent from the accounts response.
- The Goal009 plugin is absent from the accounts route annotation.
- The Goal009 `KongPlugin` resource is absent.
- The accounts body marker is preserved.
- Missing API key requests still return `401`.
- Wrong ACL requests still return `403`.
- Rate-limit and correlation headers from Goal004 remain present.
