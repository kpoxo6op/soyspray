# API Product Onboarding After Goal005

To onboard a new API product after goal005, add the product through the catalog
and the normal change-control path.

## Required Steps

1. Add `platform/catalog/api-products/<api-id>.yaml`.
2. Assign exactly one tenant owner in `platform/catalog/tenants.yaml`.
3. Classify exposure as `internal` or `external`.
4. Classify data as `internal`, `confidential`, or `restricted`.
5. Select the authn/authz model and required Kong OSS plugins.
6. Request optional tenant plugins only from the tenant allowlist.
7. Add or update API runtime manifests through committed files or renderers.
8. Run local catalog, rendered ownership, OpenAPI, and policy tests.
9. Apply through the guarded runtime workflow.
10. Capture positive smoke, negative auth, rate-limit, Admin API safety, and
    rollback evidence.

Credentials remain platform-owned. Tenant teams do not get access to credential
Secrets as part of onboarding.

Goal006 adds a narrower self-service contract path for an existing API product:
add a product contract file, add the matching decK-style state, render the
namespaced Kong resources, and prove the route-scoped contract with curl before
asking for platform approval.

Goal007 adds the matching consumer side: add a consumer contract, render the
runtime-only key-auth and ACL credential Secrets from the operator environment,
apply the `KongConsumer`, then prove positive access, `401`, `403`, rate
limiting, correlation IDs, Admin API safety, and clean rollback.
