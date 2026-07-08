# Synthetic API Security Apply And Smoke

Use this runbook for goal004 runtime validation.

## Preconditions

- `make goal003-runtime-ready` passes.
- Current Kubernetes context is the approved target context.
- `BANKLAB_ALLOW_CLUSTER_MUTATION=true`
- `BANKLAB_TARGET_CONTEXT=<approved context>`
- Required runtime credential variables are exported:
  - `BANKLAB_MOBILE_BANKING_APP_API_KEY`
  - `BANKLAB_PAYMENTS_PROCESSOR_API_KEY`
  - `BANKLAB_INTERNET_BANKING_WEB_API_KEY`
  - `BANKLAB_INTERNAL_CRM_API_KEY`
  - `BANKLAB_FRAUD_PLATFORM_API_KEY`
  - `BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY`
  - `BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET`

## Local Validation

```bash
make goal003-runtime-ready
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make validate-goal004-security
make openapi-lint
make render-synthetic-apis
make render-goal004-security
make goal004-static-test
make goal004-contract-test
make goal004-smoke-plan
make test
make policy-test
make docs
make evidence-goal-004
```

## Runtime Apply And Smoke

```bash
make synthetic-api-security-apply-and-smoke
```

The wrapper runs credential dry-run, security-control dry-run, credential apply,
security apply, positive smoke, negative tests, rate-limit tests, Admin API
safety, evidence collection, `make evidence-goal-004`, and
`make goal004-runtime-ready`.

## Rollback

```bash
make goal004-security-rollback
```

Rollback removes runtime credential Secrets by goal label and deletes the
rendered goal004 security controls. It does not roll back the already approved
goal003 synthetic APIs.
