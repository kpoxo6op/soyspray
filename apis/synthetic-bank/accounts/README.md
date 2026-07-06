# Accounts API

Synthetic account-list and account-detail API for internal banking channels.

- Host: `api.internal.banklab.test`
- Path prefix: `/accounts/v1`
- Gateway: `platform-kong/kong-internal`
- Namespace: `tenant-accounts`
- Smoke marker: `banklab-accounts-ok`

Temporary no-auth posture: goal 003 sandbox only. Goal 004 must add authentication, authorization, and rate limiting before this becomes a secured API product.
