# Consumer Onboarding

Goal007 adds a GitOps-friendly consumer onboarding path for an internal
application requesting access to an existing self-service API product.

The source contract is:

- `platform/self-service/consumer-contracts/branch-insights-app-accounts.yaml`

The contract declares the consumer application, owning team, environment,
contact, target product, allowed ACL group, runtime credential references,
review date, and expiry date.

Runtime credential values are not committed. The platform generates or supplies
`BANKLAB_BRANCH_INSIGHTS_APP_API_KEY` at rollout time, renders the key-auth and
ACL Secrets from that environment variable, and applies the `KongConsumer`
binding from the committed renderer.

The onboarding path uses the stable post-goal006 plugin set already attached to
`tenant-accounts/HTTPRoute/banklab-accounts`:

- `banklab-key-auth`
- `banklab-acl`
- `banklab-rate-limit`
- `banklab-correlation-id`

Goal007 does not reintroduce the goal006 product marker plugin. Runtime
evidence proves the onboarded consumer succeeds, missing credentials fail with
`401`, credentials without the accounts ACL fail with `403`, rate limiting still
returns `429` during a burst, correlation IDs remain present, and rollback
removes only the onboarded consumer and its runtime credential Secrets.

From the API consumer team's perspective, the request is a small contract file
with ownership and lifecycle metadata. From the platform team's perspective,
the rollout is a guarded credential render plus a committed `KongConsumer`
binding, followed by smoke, negative, rate-limit, Admin API safety, and rollback
evidence.
