# Goal: goal-007-consumer-onboarding-entitlements

## Approval Source

ChatGPT Pro approved `goal-006-self-service-api-product-contract` as
runtime-verified at evidence commit `4ee4f77`, with runtime source commit
`b16d82b`, on `kubernetes-admin@cluster.local`, then issued this goal body.

## Objective

Implement a self-service consumer onboarding and entitlement workflow for the
`accounts-self-service-health-v1` API product.

Model how an internal API consumer team requests access, receives credentials,
is bound to the correct ACL group, and proves access through positive and
negative runtime tests.

## Required Scope

- Add a GitOps-friendly consumer contract under the existing platform product
  structure.
- Declare one mock consuming application, its owning team, target API product,
  allowed ACL group, credential reference pattern, environment, contact, and
  expiry/review metadata.
- Implement the required Kong runtime configuration with the existing OSS
  plugins left after goal006 rollback: `banklab-key-auth`, `banklab-acl`,
  `banklab-rate-limit`, and `banklab-correlation-id`.
- Do not reintroduce the goal006 product contract plugin unless explicitly
  required by the design.
- Add local validation and tests proving the consumer contract renders
  correctly, rejects malformed ownership or entitlement data, avoids duplicate
  consumer names or keys, and preserves goal004, goal005, and goal006 behavior.
- Add runtime smoke tests proving:
  - valid onboarded consumer receives `200`
  - missing key receives `401`
  - valid key without the correct ACL receives `403`
  - rate limiting still applies
  - correlation ID is still present or propagated
  - Admin API safety checks pass
- Add rollback evidence proving the onboarded consumer, credential, and ACL
  binding can be removed cleanly without damaging the product route or baseline
  plugins.
- Produce evidence docs under `reports/` and `docs/decisions/` covering the
  onboarding request, approval model, runtime rollout, rollback, failure modes,
  and demo story from both API consumer and platform team perspectives.

## Non-Goals

- Do not create a new API product.
- Do not move or rename existing APIs.
- Do not commit credential values.
- Do not expose Kong Admin API.
- Do not use Kong Enterprise, Konnect, Enterprise Workspaces, Enterprise RBAC,
  or an Enterprise Dev Portal.

## Completion Gate

Goal007 is complete only when local validation passes, runtime rollout and
rollback pass, evidence is committed and pushed, and ChatGPT Pro approves the
goal as runtime-verified.
