# Customer Profile API

Synthetic customer profile API for internal CRM and servicing scenarios.

- Owner: `tenant-customer-profile-team`
- Exposure: `internal`
- Route: `api.internal.banklab.test/customers/v1`
- Smoke marker: `banklab-customer-profile-ok`
- OpenAPI: `apis/synthetic-bank/customer-profile/openapi.yaml`

This API uses synthetic data only. It is temporarily unauthenticated for goal 003 sandbox routing and must receive auth, authorization, and rate limits in goal 004.

Rollback: remove `apis/synthetic-bank/customer-profile` through the guarded synthetic API rollback path.
