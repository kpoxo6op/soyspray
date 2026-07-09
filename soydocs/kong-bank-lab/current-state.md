# Kong Bank Lab Current State

Updated: 2026-07-09

## Branch

- Repo: `/home/boris/code/soyspray`
- Branch: `kong-goals-foundation`
- Latest pushed runtime evidence commit: `7b274df`
- Goal009 source commit pushed before runtime mutation: `c9676e3`
- Goal010 source commit pushed before runtime evidence: `9b35308`
- Latest branch HEAD may be newer because of goal010 evidence or handover docs.
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
- Status: approved by ChatGPT Pro; runtime-verified
- Runtime source commit: `c9676e3`
- Runtime evidence commit approved by Pro: `7b274df`
- Runtime verification: pass
- Cluster context: `kubernetes-admin@cluster.local`
- Goal body saved at:
  - `soydocs/kong-bank-lab/goals/goal-009-kong-governed-response-headers.md`
- Evidence:
  - `reports/goal-009-summary.md`
  - `reports/goal-009-runtime-readiness.md`
  - `reports/goal-009-governed-response-headers-rollout.md`
  - `reports/goal-009-governed-response-headers-runtime.md`
  - `reports/goal-009-governed-response-headers-rollback.md`
  - `docs/decisions/goal-009-runtime-approval.md`
- Target route/service:
  - `tenant-accounts/HTTPRoute/banklab-accounts`
  - `tenant-accounts/Service/banklab-accounts-api`
- Plugin:
  - `tenant-accounts/KongPlugin/banklab-goal009-security-headers`
  - type: `response-transformer`

Goal009 adds only governed response headers and preserves existing Goal004
auth, ACL, rate-limit, and correlation-id behavior.

Runtime proof:

- readiness performed server-side dry-run without applying the plugin
- rollout applied `response-transformer` and observed all required headers
- accounts body marker, correlation ID, and rate-limit headers were preserved
- missing API key stayed `401`
- wrong ACL key stayed `403`
- rollback removed the route annotation and deleted the Goal009 `KongPlugin`
- post-rollback Goal004 positive, negative, Redis rate-limit, and Admin API
  safety checks passed
- current cluster has no `banklab-goal009-security-headers` plugin resource
  and the accounts route annotation is back to the baseline Goal004 plugin set

Local proof:

- `make validate`: pass
- `make validate-yaml`: pass
- `make validate-kustomize`: pass
- `make validate-goal008-governance`: pass
- `make validate-goal009-security-headers`: pass
- `make test`: 116 passed
- `make policy-test`: 33 passed
- `make docs`: pass
- `make evidence-goal-009`: pass

Next required order:

1. Save the Goal010 body.
2. Implement the read-only Goal010 drift guard.
3. Commit and push Goal010 source before runtime evidence.
4. Run Goal010 with mutation disabled.
5. Submit pushed Goal010 evidence to ChatGPT Pro for formal approval.

### Goal010

- Goal: `goal-010-kong-runtime-drift-guard-final-readiness`
- Status: runtime-verified locally; pending formal ChatGPT Pro approval
- Runtime source commit: `9b35308`
- Runtime verification: pass
- Cluster mutation mode: disabled
- Cluster context: `kubernetes-admin@cluster.local`
- Goal body saved at:
  - `soydocs/kong-bank-lab/goals/goal-010-kong-runtime-drift-guard-final-readiness.md`
- Expected inventory:
  - `soydocs/kong-bank-lab/goal-010-expected-runtime-inventory.yaml`
- Runtime mode:
  - read-only
  - `BANKLAB_ALLOW_CLUSTER_MUTATION=false`
- Required runtime target:
  - `make evidence-goal-010`
- Evidence:
  - `reports/goal-010-summary.md`
  - `reports/goal-010-runtime-readiness.md`
  - `reports/goal-010-kong-runtime-inventory.md`
  - `reports/goal-010-kong-drift-audit.md`
  - `reports/goal-010-behavior-regression.md`
  - `reports/goal-010-no-mutation-proof.md`
  - `reports/goal-010-readonly-rollback.md`
  - `docs/decisions/goal-010-runtime-approval.md`
  - `docs/decisions/kong-bank-lab-final-approval-candidate.md`

Goal010 must not apply, patch, delete, annotate, label, restart, scale, or
otherwise mutate Kubernetes or Kong resources. It audits that the live runtime
matches the approved post-Goal009 rollback baseline and prepares a pending
whole-project approval candidate file.

Runtime proof:

- readiness passed with mutation mode disabled
- expected inventory and live inventory compared
- accounts route annotation remained
  `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`
- Goal009 response-header plugin and annotation were absent
- Goal008 admission policy and binding were absent
- Goal004 positive smoke, negative auth, Redis rate-limit, correlation ID, and
  Kong Admin API exposure safety passed
- no-mutation proof captured resource generations before and after the audit
  and found them unchanged
- read-only rollback verification passed

## ChatGPT Pro State

ChatGPT Pro formally approved Goal008 from evidence commit `25db428` in the
visible Kong project chat.

Approval summary captured from Pro:

```text
Approved. goal-008-kong-governance-policy-as-code is approved as
runtime-verified for branch kong-goals-foundation.
```

Pro then approved Goal009 from evidence commit `7b274df` and provided the full
Goal010 body, saved under `soydocs/kong-bank-lab/goals/`.

## Current Gate

Do not submit whole-project final approval until ChatGPT Pro formally approves
Goal010 evidence. Goal010 evidence is ready to commit, push, and submit.

## Runtime Safety

No goal008 policy resources should be left applied after rollback. Verify with:

```sh
kubectl get validatingadmissionpolicy,validatingadmissionpolicybinding | rg 'banklab-kong-plugin-governance' || true
```

Expected output:

```text
No resources found
```
