# Cards API

Synthetic card-list and card-status API for internal digital channels.

- Owner: `tenant-cards-team`
- Exposure: `internal`
- Route: `api.internal.banklab.test/cards/v1`
- Smoke marker: `banklab-cards-ok`
- OpenAPI: `apis/synthetic-bank/cards/openapi.yaml`

This API uses synthetic data only. It is temporarily unauthenticated for goal 003 sandbox routing and must receive auth, authorization, and rate limits in goal 004.

Rollback: remove `apis/synthetic-bank/cards` through the guarded synthetic API rollback path.
