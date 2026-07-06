# Fraud Decisions API

Synthetic fraud decision API for internal risk scoring and transaction decision demos.

- Owner: `tenant-fraud-team`
- Exposure: `internal`
- Route: `api.internal.banklab.test/fraud/v1`
- Smoke marker: `banklab-fraud-decisions-ok`
- OpenAPI: `apis/synthetic-bank/fraud-decisions/openapi.yaml`

This API uses synthetic data only. It is temporarily unauthenticated for goal 003 sandbox routing and must receive auth, authorization, and rate limits in goal 004.

Rollback: remove `apis/synthetic-bank/fraud-decisions` through the guarded synthetic API rollback path.
