# Kong Bank Lab Handover After Goal008

Date prepared: 2026-07-09

This is the restart point for fresh Codex and ChatGPT Pro sessions.

## Repo State

- Repo: `/home/boris/code/soyspray`
- Branch: `kong-goals-foundation`
- Latest pushed runtime evidence commit: `25db428`
- Latest branch HEAD may be newer because this handover was committed after the
  runtime evidence.
- Kubernetes context used: `kubernetes-admin@cluster.local`
- Working tree at handover time: clean

Fresh Codex must verify:

```sh
git status --short --branch
git rev-parse --short HEAD
kubectl config current-context
```

Expected:

```text
## kong-goals-foundation...origin/kong-goals-foundation
<current handover commit; must contain 25db428 as an ancestor>
kubernetes-admin@cluster.local
```

Verify the runtime evidence commit is still in history:

```sh
git merge-base --is-ancestor 25db428 HEAD
```

## What Was Completed In The Previous Session

### Goal007

Goal007 was implemented, runtime-verified, approved by ChatGPT Pro, committed,
and pushed.

- Goal: `goal-007-consumer-onboarding-entitlements`
- Runtime source commit: `49b80d6`
- Evidence commit: `2527339`
- Runtime command: `make goal007-runtime-ready`
- Evidence command: `make evidence-goal-007`

Evidence:

- `reports/goal-007-summary.md`
- `reports/goal-007-consumer-onboarding-rollout.md`
- `reports/goal-007-consumer-onboarding-rollback.md`
- `docs/decisions/goal-007-runtime-approval.md`

### Goal008

Goal008 was implemented from ChatGPT Pro guidance, runtime-verified, committed,
and pushed. Formal Pro approval is still pending because the Pro chat became
stuck finalizing after acknowledging the evidence.

- Goal: `goal-008-kong-governance-policy-as-code`
- Runtime source commit: `cfcd2ec`
- Evidence commit: `25db428`
- Runtime command: `make goal008-runtime-ready`
- Evidence command: `make evidence-goal-008`

Evidence:

- `reports/goal-008-summary.md`
- `reports/goal-008-governance-policy-rollout.md`
- `reports/goal-008-governance-policy-rollback.md`
- `docs/decisions/goal-008-runtime-approval.md`

Goal008 runtime proof:

- Kubernetes-native `ValidatingAdmissionPolicy` and binding applied
- safe `response-transformer` KongPlugin fixture accepted by server dry-run
- unsafe `request-transformer` KongPlugin fixture denied by the allowlist policy
- goal004 smoke and negative tests passed while the policy was active
- rollback removed the binding before the policy
- unsafe fixture became server-dry-run admissible after rollback
- goal004 smoke, Redis rate limit, and Kong Admin API safety passed after
  rollback
- no `banklab-kong-plugin-governance` admission resources remained after
  rollback

## Current Programme Gate

Do not start goal009 yet.

The next action is to ask ChatGPT Pro to formally approve goal008 at evidence
commit `25db428` and provide the full body for goal009.

If Pro approves goal008 and gives goal009, save the full goal009 body under
`soydocs/kong-bank-lab/goals/` before implementing.

## Commands Already Passed For Goal008

Local:

```sh
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make validate-goal004-security
make validate-goal005-tenancy
make validate-goal006-product
make validate-goal007-consumer
make validate-goal008-governance
make openapi-lint
make render-synthetic-apis
make render-goal004-security
make render-goal005-tenancy-rbac
make render-goal006-product-contract
make render-goal007-consumer-onboarding
make render-goal008-governance-policy
make goal004-static-test
make goal005-static-test
make goal006-static-test
make goal007-static-test
make goal008-static-test
make goal008-contract-test
make test
make policy-test
make docs
make evidence-goal-008
```

Runtime:

```sh
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local
make goal008-runtime-ready
```

## ChatGPT Pro Prompt

Paste this into a fresh ChatGPT Pro Kong project chat:

```text
We are restarting the Kong bank-lab programme from a saved repo handover.

Repo: /home/boris/code/soyspray
Branch: kong-goals-foundation
Latest pushed runtime evidence commit: 25db428
Latest branch HEAD may be newer because post-goal008 handover docs were committed after runtime evidence.
Current handover file: soydocs/kong-bank-lab/handover-2026-07-09-post-goal-008.md
Current state file: soydocs/kong-bank-lab/current-state.md
Kubernetes context used for runtime evidence: kubernetes-admin@cluster.local

Please approve goal008 and provide goal009 only if the evidence is sufficient.
Do not start a new validation loop unless something concrete is missing.

Goal008:
- Goal: goal-008-kong-governance-policy-as-code
- Runtime source commit: cfcd2ec
- Evidence commit: 25db428
- Status in repo: runtime-verified locally; pending formal Pro approval

Evidence files:
- reports/goal-008-summary.md
- reports/goal-008-governance-policy-rollout.md
- reports/goal-008-governance-policy-rollback.md
- docs/decisions/goal-008-runtime-approval.md

Runtime evidence:
- BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local make goal008-runtime-ready: pass
- make evidence-goal-008: pass
- reports/goal-008-summary.md: Status: pass; runtime-verified
- reports/goal-008-governance-policy-rollout.md: Status: pass
- reports/goal-008-governance-policy-rollback.md: Status: pass
- docs/decisions/goal-008-runtime-approval.md: Status: pending approval

Runtime proof:
- ValidatingAdmissionPolicy and ValidatingAdmissionPolicyBinding applied.
- safe response-transformer KongPlugin fixture accepted by server dry-run.
- unsafe request-transformer KongPlugin fixture denied by the governance allowlist.
- goal004 positive smoke and negative auth behavior passed while the policy was active.
- rollback removed the binding before the policy.
- unsafe fixture became server-dry-run admissible after rollback.
- goal004 smoke, Redis rate-limit behavior, and Kong Admin API safety passed after rollback.
- current cluster has no banklab-kong-plugin-governance admission resources.

Local proof:
- make validate: pass
- make validate-yaml: pass
- make validate-kustomize: pass
- make validate-goal008-governance: pass
- make test: 109 passed
- make policy-test: 33 passed
- make docs: pass

Previous visible Pro response in the stuck chat:
"The pushed GitHub evidence at 25db428 is available and supports the programme decision, including runtime-verified status, deny-mode admission behavior, and rollback proof."

Please either:
1. approve goal-008-kong-governance-policy-as-code as runtime-verified for branch kong-goals-foundation at evidence commit 25db428, with runtime source commit cfcd2ec, and provide the full body for goal009; or
2. give exact corrections and exact commands to rerun.

If approved, keep goal009 small, OSS/Kubernetes/GitOps-compatible, and provide exact scope, non-goals, local tests, runtime evidence, rollback evidence, docs, and completion gate.
```

## Fresh Codex Restart Prompt

Start fresh Codex with:

```text
Continue the Kong bank-lab programme from repo handover.

Repo: /home/boris/code/soyspray
Branch: kong-goals-foundation
Latest pushed runtime evidence commit should be 25db428.
Branch HEAD may be newer due post-goal008 handover docs; verify HEAD and confirm 25db428 is an ancestor.
Target Kubernetes context: kubernetes-admin@cluster.local

Read:
- AGENTS.md
- soydocs/kong-bank-lab/handover-2026-07-09-post-goal-008.md
- soydocs/kong-bank-lab/current-state.md
- reports/goal-008-summary.md
- docs/decisions/goal-008-runtime-approval.md

First verify:
- git status --short --branch
- git rev-parse --short HEAD
- git merge-base --is-ancestor 25db428 HEAD
- kubectl config current-context

Do not start goal009 until ChatGPT Pro formally approves goal008 and provides a usable goal009 body.

Use the visible ChatGPT Pro Kong project chat for approval. If the existing chat is laggy or stuck finalizing, start a fresh project chat and paste the Pro prompt from the handover file.

After Pro approves goal008, save the full goal009 body under soydocs/kong-bank-lab/goals/ before implementing. Keep cluster changes guarded and push source commits before runtime mutation.
```
