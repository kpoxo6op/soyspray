# Open Banking Partner API

Synthetic external partner API for open-banking style onboarding and exposure demos.

- Owner: `tenant-open-banking-team`
- Exposure: `external`
- Route: `api.external.banklab.test/open-banking/v1`
- Smoke marker: `banklab-open-banking-ok`
- OpenAPI: `apis/synthetic-bank/open-banking/openapi.yaml`

This API uses synthetic data only. It is temporarily unauthenticated for goal 003 sandbox routing and must receive auth, authorization, and rate limits in goal 004.

Rollback: remove `apis/synthetic-bank/open-banking` through the guarded synthetic API rollback path.
