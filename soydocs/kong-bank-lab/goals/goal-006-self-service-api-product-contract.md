# Goal: goal-006-self-service-api-product-contract

## Approval Source

ChatGPT Pro fresh project chat for `kong` issued the implementation direction.
The Pro response stalled while finalizing, but both attempts gave the same
guidance: make goal006 a compact OSS/Kubernetes/GitOps increment using decK,
OSS Kong plugins, an existing mock API, and curl proof while avoiding
Enterprise-only or Konnect-only controls.

## Objective

Implement one self-service API product contract for the existing `accounts`
synthetic API.

The goal moves the lab from "tenant ownership exists" to "a tenant can publish
a small product contract through Git, and Kong enforces an observable
route-scoped contract from that committed state."

## Scope

- Use the existing `accounts` API in `tenant-accounts`.
- Use the existing `retail-accounts` owning team.
- Add one product contract artifact.
- Add one decK-style declarative state artifact.
- Add one OSS `response-transformer` KongPlugin scoped to the accounts route.
- Prove the product marker appears only after the committed contract is applied.
- Prove goal004 auth, ACL, correlation ID, rate-limit headers, and Admin API
  exposure safety still hold.

## Non-Goals

- Do not create a seventh API.
- Do not introduce Keycloak, SSO, Kong Enterprise RBAC, Enterprise Workspaces,
  Konnect, Kong Manager, or an Enterprise Dev Portal.
- Do not expose the Kong Admin API.
- Do not commit, print, or report credential values.
- Do not weaken goal004 or goal005 controls.

## Required Files

- `platform/self-service/api-products/accounts-self-service-health-v1.yaml`
- `platform/kong/deck/goal006/accounts-self-service-product.yaml`
- `scripts/goal006_product_contract_config.py`
- `scripts/render_goal006_product_contract.py`
- `scripts/validate_goal006_product_contract.py`
- `scripts/goal006/product_contract_apply_smoke.sh`
- `scripts/goal006/product_contract_rollback_smoke.sh`
- `scripts/goal006/runtime_ready.sh`
- `tests/goal006/test_product_contract.py`
- `docs/platform/self-service-product-contracts.md`
- `docs/runbooks/goal-006-product-contract-rollback.md`
- `docs/decisions/goal-006-runtime-approval.md`
- `reports/goal-006-summary.md`
- `reports/goal-006-product-contract-rollout.md`
- `reports/goal-006-product-contract-rollback.md`

## Local Validation Commands

```sh
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make validate-goal004-security
make validate-goal005-tenancy
make validate-goal006-product
make openapi-lint
make render-synthetic-apis
make render-goal004-security
make render-goal005-tenancy-rbac
make render-goal006-product-contract
make goal004-static-test
make goal004-contract-test
make goal005-static-test
make goal005-contract-test
make goal006-static-test
make goal006-contract-test
make test
make policy-test
make docs
```

## Runtime Commands

All cluster mutation commands must run on `kubernetes-admin@cluster.local` with
the mutation guard variables set.

```sh
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local
make goal006-product-contract-apply-and-smoke
make goal006-product-contract-rollback-and-smoke
make goal006-runtime-ready
make evidence-goal-006
```

## Evidence Contract

Evidence must show:

- product contract and decK-style state reference the existing `accounts` API
  and `retail-accounts` tenant
- rendered resources are namespaced and OSS-compatible
- route plugin chain preserves goal004 plugins and adds only the goal006
  product marker plugin
- positive curl with the accounts API key returns `200`,
  `banklab-accounts-ok`, `X-Banklab-Product-Contract`, correlation ID, and
  rate-limit headers
- missing API key still returns `401`
- wrong ACL key still returns `403`
- rollback removes only the goal006 marker plugin and leaves goal004 and
  goal005 behavior intact
- Kong Admin API exposure remains safe

## Pro Approval Gate

After runtime evidence is committed and pushed, ask ChatGPT Pro to approve:

```text
Please approve goal-006-self-service-api-product-contract as runtime-verified.
Evidence commit: <short-sha>
Cluster context: kubernetes-admin@cluster.local
Runtime status: pass
```

## Stop Or Continue

After Pro approves goal006, ask Pro to issue goal007 in the same compact style.
If the Pro chat becomes laggy, start a fresh `kong` project chat and continue.
