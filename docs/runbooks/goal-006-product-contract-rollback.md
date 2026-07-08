# Goal006 Product Contract Rollback

Use this runbook when the goal006 product contract marker must be removed from
the accounts API.

## Command

```sh
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local
make goal006-product-contract-rollback-and-smoke
```

## Expected Result

- `KongPlugin/tenant-accounts/goal006-product-contract-header` is deleted.
- `HTTPRoute/tenant-accounts/banklab-accounts` no longer references the
  goal006 plugin.
- The accounts health endpoint still returns `200` for the valid accounts
  client.
- `X-Banklab-Product-Contract` is absent after rollback.
- Goal004 correlation ID and rate-limit headers remain present.
