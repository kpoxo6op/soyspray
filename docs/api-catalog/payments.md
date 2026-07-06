# Payments API

Synthetic payment initiation and payment-status API for internal payment flows.

- Owner: `tenant-payments-team`
- Exposure: `internal`
- Route: `api.internal.banklab.test/payments/v1`
- Smoke marker: `banklab-payments-ok`
- OpenAPI: `apis/synthetic-bank/payments/openapi.yaml`

This API uses synthetic data only. It is temporarily unauthenticated for goal 003 sandbox routing and must receive auth, authorization, and rate limits in goal 004.

Rollback: remove `apis/synthetic-bank/payments` through the guarded synthetic API rollback path.
