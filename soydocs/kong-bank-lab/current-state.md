# Kong Bank Lab Current State

Updated: 2026-07-09

## Branch

- Repo: `/home/boris/code/soyspray`
- Branch: `kong-goals-foundation`
- Latest pushed commit: `25db428`
- Kubernetes context used for runtime checks: `kubernetes-admin@cluster.local`

Fresh sessions must first verify:

```sh
git status --short --branch
git rev-parse --short HEAD
kubectl config current-context
```

Expected state at this handover:

```text
## kong-goals-foundation...origin/kong-goals-foundation
25db428
kubernetes-admin@cluster.local
```

## Completed And Approved

### Goal006

- Goal: `goal-006-self-service-api-product-contract`
- Status: approved by ChatGPT Pro; runtime-verified
- Runtime source commit: `b16d82b`
- Evidence commit approved by Pro: `4ee4f77`
- Evidence:
  - `reports/goal-006-summary.md`
  - `reports/goal-006-product-contract-rollout.md`
  - `reports/goal-006-product-contract-rollback.md`
  - `docs/decisions/goal-006-runtime-approval.md`

### Goal007

- Goal: `goal-007-consumer-onboarding-entitlements`
- Status: approved by ChatGPT Pro; runtime-verified
- Runtime source commit: `49b80d6`
- Evidence commit approved by Pro: `2527339`
- Evidence:
  - `reports/goal-007-summary.md`
  - `reports/goal-007-consumer-onboarding-rollout.md`
  - `reports/goal-007-consumer-onboarding-rollback.md`
  - `docs/decisions/goal-007-runtime-approval.md`

## Latest Runtime State

### Goal008

- Goal: `goal-008-kong-governance-policy-as-code`
- Status: runtime-verified locally; pending formal ChatGPT Pro approval
- Runtime source commit: `cfcd2ec`
- Runtime evidence commit pushed: `25db428`
- Runtime verification: pass
- Cluster context: `kubernetes-admin@cluster.local`
- Evidence:
  - `reports/goal-008-summary.md`
  - `reports/goal-008-governance-policy-rollout.md`
  - `reports/goal-008-governance-policy-rollback.md`
  - `docs/decisions/goal-008-runtime-approval.md`

Goal008 implemented a Kubernetes-native `ValidatingAdmissionPolicy` and binding
for KongPlugin allowlisting.

Runtime proof:

- policy and binding applied
- safe `response-transformer` KongPlugin fixture accepted by server dry-run
- unsafe `request-transformer` KongPlugin fixture denied by governance policy
- goal004 smoke and negative tests passed while the policy was active
- rollback removed the binding before the policy
- unsafe fixture became server-dry-run admissible after rollback
- goal004 smoke, Redis rate limit, and Kong Admin API safety passed after
  rollback
- current cluster has no `banklab-kong-plugin-governance` admission resources

Local proof:

- `make validate`: pass
- `make validate-yaml`: pass
- `make validate-kustomize`: pass
- `make validate-synthetic-apis`: pass
- `make validate-goal004-security`: pass
- `make validate-goal005-tenancy`: pass
- `make validate-goal006-product`: pass
- `make validate-goal007-consumer`: pass
- `make validate-goal008-governance`: pass
- `make openapi-lint`: pass
- render targets through goal008: pass
- `make test`: 109 passed
- `make policy-test`: 33 passed
- `make docs`: pass
- `make evidence-goal-008`: pass

## ChatGPT Pro State

Pro received the goal008 approval packet for evidence commit `25db428`.

Visible Pro response:

```text
The pushed GitHub evidence at 25db428 is available and supports the programme
decision, including runtime-verified status, deny-mode admission behavior, and
rollback proof.
```

Then the Pro answer became stuck at `Finalizing answer` before providing a clean
formal approval or a full goal009 body.

## Current Gate

Do not start goal009 until ChatGPT Pro formally approves
`goal-008-kong-governance-policy-as-code` and provides a usable goal009 body.

If Pro is still laggy, start a fresh ChatGPT Pro project chat and paste the
prompt from `soydocs/kong-bank-lab/handover-2026-07-09-post-goal-008.md`.

## Runtime Safety

No goal008 policy resources should be left applied after rollback. Verify with:

```sh
kubectl get validatingadmissionpolicy,validatingadmissionpolicybinding | rg 'banklab-kong-plugin-governance' || true
```

Expected output:

```text
No resources found
```
