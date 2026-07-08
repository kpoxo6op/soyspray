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
