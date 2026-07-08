# Goal004 Security Smoke Plan

Status: pass

Generated at: 2026-07-08T23:14:16+12:00

## Positive checks
- `accounts`: `mobile-banking-app` API key returns 200 and marker `banklab-accounts-ok`; plugins `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- `payments`: `payments-processor` API key returns 200 and marker `banklab-payments-ok`; plugins `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- `cards`: `internet-banking-web` API key returns 200 and marker `banklab-cards-ok`; plugins `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- `customer-profile`: `internal-crm` API key returns 200 and marker `banklab-customer-profile-ok`; plugins `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- `fraud-decisions`: `fraud-platform` API key returns 200 and marker `banklab-fraud-decisions-ok`; plugins `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`.
- `open-banking`: `external-fintech-partner` JWT returns 200 and marker `banklab-open-banking-ok`; plugins `banklab-jwt,banklab-acl,banklab-rate-limit,banklab-correlation-id`.

## Negative checks
- Missing API key returns 401.
- Invalid API key returns 401.
- Valid API key for the wrong ACL group returns 403.
- Missing JWT returns 401.
- Invalid JWT signature returns 401.
- Expired JWT returns 401.
- Unknown host and path remain 404.
- Admin API external probe still fails.

## Rate limit check
- A valid client exceeds the Redis-backed `second: 3` rate limit and receives 429.
