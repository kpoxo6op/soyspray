# Save Point: Post Goal 005

Created: 2026-07-09T00:40:00+12:00

## Current State

- Branch: `kong-goals-foundation`
- Evidence commit approved by ChatGPT Pro: `c032c61`
- Save point commit: this document's commit
- Kubernetes context used for runtime evidence: `kubernetes-admin@cluster.local`
- Goal 006 allowed to start: no
- Stop condition: stop before `goal-006-keycloak-sso-platform-tools`

## Goal 004

- Goal body: `soydocs/kong-bank-lab/goals/goal-004-auth-rate-limit-security.md`
- Evidence summary: `reports/goal-004-summary.md`
- Runtime approval: `docs/decisions/goal-004-runtime-approval.md`
- Pro approval status: approved
- Runtime status: pass; runtime-verified

Passed goal004 commands:

- `make synthetic-api-security-apply-and-smoke`
- `make goal004-runtime-credentials-apply`
- `make goal004-security-apply`
- `make goal004-security-smoke`
- `make goal004-security-negative-test`
- `make goal004-rate-limit-test`
- `make kong-admin-exposure-test`
- `make goal004-runtime-ready`
- `make evidence-goal-004`

Goal004 cluster mutations performed:

- Runtime credential Secrets generated from local/operator environment and applied to `synthetic-clients`.
- Redis-backed rate-limit runtime resources applied in `platform-kong`.
- Goal004 KongPlugin, KongConsumer, HTTPRoute annotation, and supporting NetworkPolicy resources applied.

## Goal 005

- Goal body: `soydocs/kong-bank-lab/goals/goal-005-tenancy-rbac-change-control.md`
- Evidence summary: `reports/goal-005-summary.md`
- RBAC runtime evidence: `reports/goal-005-rbac-runtime.md`
- Sample change rollout evidence: `reports/goal-005-change-rollout.md`
- Sample change rollback evidence: `reports/goal-005-change-rollback.md`
- Runtime approval: `docs/decisions/goal-005-runtime-approval.md`
- Pro approval status: approved
- Runtime status: pass; runtime-verified

Passed goal005 commands:

- `make validate`
- `make validate-yaml`
- `make validate-kustomize`
- `make validate-synthetic-apis`
- `make validate-goal004-security`
- `make validate-goal005-tenancy`
- `make openapi-lint`
- `make render-synthetic-apis`
- `make render-goal004-security`
- `make render-goal005-tenancy-rbac`
- `make render-goal005-change`
- `make goal004-static-test`
- `make goal004-contract-test`
- `make goal005-static-test`
- `make goal005-contract-test`
- `make test`
- `make policy-test`
- `make docs`
- `make synthetic-api-security-apply-and-smoke`
- `make goal005-tenancy-rbac-apply`
- `make goal005-rbac-smoke`
- `make goal005-change-apply-and-smoke`
- `make goal005-change-rollback-and-smoke`
- `make goal005-runtime-ready`
- `make evidence-goal-005`

Goal005 cluster mutations performed:

- Applied stable tenant namespace metadata, tenant service accounts, Roles, RoleBindings, and platform catalog ConfigMap.
- Patched six synthetic API HTTPRoutes with goal005 ownership metadata.
- Applied sample `KongPlugin/tenant-accounts/goal005-normal-change-header`.
- Patched `HTTPRoute/tenant-accounts/banklab-accounts` to attach the sample plugin.
- Rolled back the sample change by deleting only the sample plugin and restoring the stable accounts route annotation.

## Pro Corrections To Carry Forward

- None. ChatGPT Pro approved goal005 and said not to issue goal006 yet.

## Fresh-Context Continuation Pointers

- Programme rule: `soydocs/kong-bank-lab/post-goal-005-savepoint.md`
- Current state: `soydocs/kong-bank-lab/current-state.md`
- Goal004 body: `soydocs/kong-bank-lab/goals/goal-004-auth-rate-limit-security.md`
- Goal005 body: `soydocs/kong-bank-lab/goals/goal-005-tenancy-rbac-change-control.md`
- Goal005 catalog: `platform/catalog/tenants.yaml` and `platform/catalog/api-products/`
- Goal005 runtime scripts: `scripts/goal005/`
- Goal005 evidence: `reports/goal-005-summary.md`

## Stop

Do not start goal006 from this conversation. Start a fresh Codex and fresh Pro
chat before requesting or implementing `goal-006-keycloak-sso-platform-tools`.
