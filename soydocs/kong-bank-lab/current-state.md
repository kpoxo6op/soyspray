# Kong Bank Lab Current State

Updated: 2026-07-09

## Branch

- Repo: `/home/boris/code/soyspray`
- Branch: `kong-goals-foundation`
- Latest pushed runtime evidence commit: `25db428`
- Latest branch HEAD may be newer because of post-goal008 handover docs.
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
<current handover commit; must contain 25db428 as an ancestor>
kubernetes-admin@cluster.local
```

Verify the runtime evidence commit is still in history:

```sh
git merge-base --is-ancestor 25db428 HEAD
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

### Goal008

- Goal: `goal-008-kong-governance-policy-as-code`
- Status: approved by ChatGPT Pro; runtime-verified
- Runtime source commit: `cfcd2ec`
- Runtime evidence commit approved by Pro: `25db428`
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

## Latest Source State

### Goal009

- Goal: `goal-009-kong-governed-response-headers`
- Status: source implemented locally; runtime evidence not yet run
- Goal body saved at:
  - `soydocs/kong-bank-lab/goals/goal-009-kong-governed-response-headers.md`
- Target route/service:
  - `tenant-accounts/HTTPRoute/banklab-accounts`
  - `tenant-accounts/Service/banklab-accounts-api`
- Plugin:
  - `tenant-accounts/KongPlugin/banklab-goal009-security-headers`
  - type: `response-transformer`

Goal009 adds only governed response headers and preserves existing Goal004
auth, ACL, rate-limit, and correlation-id behavior.

Local source proof before runtime mutation:

- `make validate`: pass
- `make validate-yaml`: pass
- `make validate-kustomize`: pass
- `make validate-goal008-governance`: pass
- `make validate-goal009-security-headers`: pass
- `make test`: 116 passed
- `make policy-test`: 33 passed
- `make docs`: pass

Next required order:

1. Commit and push the Goal009 source changes.
2. Run guarded runtime readiness:
   `BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local make goal009-runtime-ready`
3. Run guarded runtime evidence:
   `BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local make evidence-goal-009`
4. Commit and push runtime evidence.
5. Ask ChatGPT Pro to approve Goal009 runtime evidence before starting Goal010.

## ChatGPT Pro State

ChatGPT Pro formally approved Goal008 from evidence commit `25db428` in the
visible Kong project chat.

Approval summary captured from Pro:

```text
Approved. goal-008-kong-governance-policy-as-code is approved as
runtime-verified for branch kong-goals-foundation.
```

Pro then provided the full Goal009 body, saved under
`soydocs/kong-bank-lab/goals/`.

## Current Gate

Do not run Goal009 runtime mutation until the source commit has been pushed.
After runtime evidence is pushed, do not start Goal010 until ChatGPT Pro
approves Goal009.

## Runtime Safety

No goal008 policy resources should be left applied after rollback. Verify with:

```sh
kubectl get validatingadmissionpolicy,validatingadmissionpolicybinding | rg 'banklab-kong-plugin-governance' || true
```

Expected output:

```text
No resources found
```
