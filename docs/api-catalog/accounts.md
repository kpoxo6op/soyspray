# Accounts API

Synthetic account-list and account-detail API for internal banking channels.

- Owner: `tenant-accounts-team`
- Exposure: `internal`
- Route: `api.internal.banklab.test/accounts/v1`
- Smoke marker: `banklab-accounts-ok`
- OpenAPI: `apis/synthetic-bank/accounts/openapi.yaml`

This API uses synthetic data only. It is temporarily unauthenticated for goal 003 sandbox routing and must receive auth, authorization, and rate limits in goal 004.

Rollback: remove `apis/synthetic-bank/accounts` through the guarded synthetic API rollback path.
