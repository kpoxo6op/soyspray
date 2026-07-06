# Payments API

Synthetic payment initiation and payment-status API for internal payment flows.

- Host: `api.internal.banklab.test`
- Path prefix: `/payments/v1`
- Gateway: `platform-kong/kong-internal`
- Namespace: `tenant-payments`
- Smoke marker: `banklab-payments-ok`

Temporary no-auth posture: goal 003 sandbox only. Goal 004 must add authentication, authorization, and rate limiting before this becomes a secured API product.
