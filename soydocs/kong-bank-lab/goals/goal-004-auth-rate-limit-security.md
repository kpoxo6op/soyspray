# Goal: goal-004-auth-rate-limit-security

## Objective

Implement the first security-control layer for the synthetic banking API
platform on the existing Kong OSS, DB-less, Gateway API baseline.

Use only Kubernetes-native Kong Ingress Controller resources and Kubernetes
controls. Add authentication, authorization, Redis-backed rate limiting,
correlation IDs, local validation, guarded runtime validation, negative tests,
and evidence.

This goal starts from gate003 runtime approval. Do not re-open, rewrite, or
loop on goal003 validation. Use `make goal003-runtime-ready` once as the
precondition, then move forward into goal004.

## Baseline

- Repository: `kpoxo6op/soyspray`
- Branch: `kong-goals-foundation`
- Gate003 commit: `a8dd9fd`
- Required precondition: `make goal003-runtime-ready` passes
- Current Kong baseline: Kong OSS only, DB-less, KIC managed through Kubernetes resources
- Current API layer: six synthetic bank APIs are already runtime verified
- Current auth state: no auth and no rate limiting, explicitly deferred to goal004

## Hard Constraints

- Keep Kong OSS only.
- Do not add Kong Enterprise, Konnect, Kong Manager, Kong Portal, Kong Workspaces, Kong RBAC, OpenID Connect plugin, Request Validator plugin, Rate Limiting Advanced plugin, MTLS Auth plugin, or any Enterprise-only plugin.
- Do not configure Kong through direct Admin API writes.
- Do not commit API keys, JWT secrets, private keys, generated tokens, `.env` files, kubeconfigs, PEM files, or credential Secret manifests.
- Do not add real customer data.
- Keep CI cluster-free.
- Runtime apply, runtime credentials, smoke tests, negative tests, rollback, and evidence collection must be explicit local operator actions.
- Every cluster mutation target must call `platform/kong/scripts/require-cluster-mutation-permission.sh`.
- Do not mutate or regenerate gate003 approval evidence except to read it as a precondition.

## Security Model

Use these API-to-client controls:

- `accounts`: Kong OSS `key-auth`; client `mobile-banking-app`; ACL group `banklab-accounts`; internal only.
- `payments`: Kong OSS `key-auth`; client `payments-processor`; ACL group `banklab-payments`; internal only.
- `cards`: Kong OSS `key-auth`; client `internet-banking-web`; ACL group `banklab-cards`; internal only.
- `customer-profile`: Kong OSS `key-auth`; client `internal-crm`; ACL group `banklab-customer-profile`; internal only.
- `fraud-decisions`: Kong OSS `key-auth`; client `fraud-platform`; ACL group `banklab-fraud-decisions`; internal only.
- `open-banking`: Kong OSS `jwt`; client `external-fintech-partner`; ACL group `banklab-open-banking`; external only.

All six APIs must also have Kong OSS `acl`, Kong OSS `rate-limiting` with Redis
policy, Kong OSS `correlation-id`, no external exposure expansion beyond
`open-banking`, no wildcard hostnames, no catch-all paths, and no externally
exposed Admin API.

## Runtime Credential Model

Create `KongConsumer` resources in the `synthetic-clients` namespace. Each
consumer references credential Secret names, but the Secret objects themselves
must not be committed.

Runtime credential Secrets are generated only from local environment variables
and piped directly to `kubectl apply -f -`.

Required runtime env vars:

- `BANKLAB_MOBILE_BANKING_APP_API_KEY`
- `BANKLAB_PAYMENTS_PROCESSOR_API_KEY`
- `BANKLAB_INTERNET_BANKING_WEB_API_KEY`
- `BANKLAB_INTERNAL_CRM_API_KEY`
- `BANKLAB_FRAUD_PLATFORM_API_KEY`
- `BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY`
- `BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET`

The runtime credential generator must fail closed if any value is missing,
placeholder-like, too short, duplicated, or equal to a known example value. It
must never print secret values to reports or logs.

## Implementation Requirements

Add a goal004 security-control layer under:

- `platform/kong/security-controls/`
- `scripts/goal004_security_config.py`
- `scripts/render_goal004_security_controls.py`
- `scripts/render_goal004_runtime_credentials.py`
- `scripts/validate_goal004_security_controls.py`
- `scripts/generate_goal004_smoke_plan.py`

The static renderer must produce Kubernetes resources for:

- Redis Deployment and Service for rate-limit counters
- Redis NetworkPolicy
- Kong egress NetworkPolicy from Kong gateway pods to Redis on TCP 6379 only
- KongPlugin resources in the relevant tenant namespaces
- Patched HTTPRoute resources that add the required `konghq.com/plugins` annotation
- KongConsumer resources in `synthetic-clients`
- No Secret resources

Use these plugin names:

- `banklab-key-auth`
- `banklab-jwt`
- `banklab-acl`
- `banklab-rate-limit`
- `banklab-correlation-id`

Internal API HTTPRoutes use:

```yaml
konghq.com/plugins: banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id
```

The Open Banking HTTPRoute uses:

```yaml
konghq.com/plugins: banklab-jwt,banklab-acl,banklab-rate-limit,banklab-correlation-id
```

Do not use KongPlugin `ordering`.

## Plugin Baselines

Key Auth:

```yaml
plugin: key-auth
config:
  key_names:
  - apikey
  key_in_header: true
  key_in_query: false
  key_in_body: false
  hide_credentials: true
  run_on_preflight: false
```

JWT:

```yaml
plugin: jwt
config:
  key_claim_name: iss
  claims_to_verify:
  - exp
  secret_is_base64: false
  run_on_preflight: false
```

ACL:

```yaml
plugin: acl
config:
  allow:
  - <api-specific-acl-group>
  hide_groups_header: true
```

Rate limiting:

```yaml
plugin: rate-limiting
config:
  policy: redis
  limit_by: consumer
  second: 3
  fault_tolerant: false
  hide_client_headers: false
  redis:
    host: banklab-rate-limit-redis.platform-kong.svc.cluster.local
    port: 6379
    database: 0
    timeout: 2000
```

Correlation ID:

```yaml
plugin: correlation-id
config:
  header_name: X-Banklab-Correlation-ID
  generator: uuid
  echo_downstream: true
```

## Required Makefile Targets

Local targets:

- `validate-goal004-security`
- `render-goal004-security`
- `goal004-static-test`
- `goal004-contract-test`
- `goal004-smoke-plan`
- `evidence-goal-004`

Guarded runtime targets:

- `goal004-security-dry-run`
- `goal004-runtime-credentials-dry-run`
- `goal004-runtime-credentials-apply`
- `goal004-security-apply`
- `goal004-security-smoke`
- `goal004-security-negative-test`
- `goal004-rate-limit-test`
- `goal004-security-rollback`
- `goal004-runtime-ready`

## Runtime Validation Requirements

Positive checks:

- Accounts with valid `mobile-banking-app` API key returns 200.
- Payments with valid `payments-processor` API key returns 200.
- Cards with valid `internet-banking-web` API key returns 200.
- Customer Profile with valid `internal-crm` API key returns 200.
- Fraud Decisions with valid `fraud-platform` API key returns 200.
- Open Banking with valid JWT returns 200.
- Each successful response includes `X-Banklab-Correlation-ID`.
- Each successful response still returns the expected synthetic marker.

Negative checks:

- Missing API key returns 401.
- Invalid API key returns 401.
- Valid API key for wrong ACL group returns 403.
- Missing JWT returns 401.
- Invalid JWT signature returns 401.
- Expired JWT returns 401.
- Internal APIs remain unavailable through the external hostname.
- Unknown host remains 404.
- Unknown path remains 404.
- Admin API external probe still fails.

Rate-limit check:

- A valid client exceeds the configured Redis-backed limit and receives 429.
- Evidence confirms the rate-limit plugin is using Redis policy, not local policy.

## Evidence Files

Add or update:

- `reports/goal-004-summary.md`
- `reports/goal004-security-smoke-plan.md`
- `reports/goal004-security-runtime-state.md`
- `reports/goal004-security-smoke-results.md`
- `reports/goal004-security-negative-test-results.md`
- `reports/goal004-rate-limit-results.md`
- `reports/gate-004-auth-rate-limit-security-runtime-summary.md`
- `platform/kong/security-controls/RUNTIME-APPLY-EXECUTION-LOG.md`
- `platform/kong/security-controls/RUNTIME-SMOKE-RESULTS.md`
- `platform/kong/security-controls/RUNTIME-NEGATIVE-TEST-RESULTS.md`
- `platform/kong/security-controls/RUNTIME-RATE-LIMIT-RESULTS.md`
- `platform/kong/security-controls/RUNTIME-ADMIN-API-SAFETY-RESULTS.md`
- `docs/decisions/goal-004-runtime-approval.md`

Initial runtime evidence may be `Status: not run` until explicit guarded runtime
execution occurs. The final runtime-ready target may pass only when apply,
smoke, negative tests, rate-limit tests, Admin API safety, and evidence are all
`Status: pass`.

## Required Final Local Command Set

Run and record:

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

Do not run guarded runtime targets unless explicit mutation permission and target
Kubernetes context are supplied.

## Acceptance Criteria

Local acceptance passes when the goal003 runtime-ready precondition passes, all
required local validation commands pass, no API keys or credential Secrets are
committed, CI remains cluster-free, Kong OSS boundary is preserved, rendered
security controls are Kubernetes-native, evidence report is generated, and the
runtime gate fails closed before runtime evidence.

Runtime acceptance passes only after explicit guarded execution proves
credentials were created only from local env vars, security controls were
applied, all positive smoke checks pass, all negative checks pass, Redis-backed
rate limiting returns 429, Admin API is still not externally exposed, and
`make goal004-runtime-ready` passes.

## Hard Stop

Stop after goal004 evidence is generated and goal004 approval is reported. Do
not start goal005 until ChatGPT Pro approves goal004.
