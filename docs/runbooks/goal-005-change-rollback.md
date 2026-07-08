# Goal005 Sample Change Rollback

The sample normal change adds `X-Goal005-Change-Id:
goal-005-normal-change` to the `accounts` API. Rollback removes only the sample
KongPlugin and restores the stable HTTPRoute plugin annotation.

## Rollback Command

```sh
make goal005-change-rollback-and-smoke
```

## Expected Result

- `KongPlugin/tenant-accounts/goal005-normal-change-header` is deleted.
- `HTTPRoute/tenant-accounts/banklab-accounts` keeps the goal004 security
  plugin chain and no longer references the goal005 sample plugin.
- A valid accounts request returns HTTP 200 and the `banklab-accounts-ok`
  marker.
- `X-Banklab-Correlation-ID` remains present.
- Rate-limit headers remain present.
- `X-Goal005-Change-Id` is absent.
- Missing credentials still return 401 and wrong-ACL credentials still return
  403.
