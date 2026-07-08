# Kong Bank Lab Current State

Updated: 2026-07-09

## Branch

- Branch: `kong-goals-foundation`
- Latest pushed source checkpoint before runtime evidence: `49b80d6`
- Latest pushed evidence checkpoint: this document's commit once committed and
  pushed
- Before approval, confirm the current commit with `git rev-parse --short HEAD`
  and put that value in the approval block.

## Previous Runtime State

Goal006 was implemented from fresh ChatGPT Pro guidance, runtime-verified, and
approved by ChatGPT Pro.

Accepted local/runtime state:

- Goal: `goal-006-self-service-api-product-contract`
- Status: approved; runtime-verified
- Branch: `kong-goals-foundation`
- Evidence commit approved by Pro: `4ee4f77`
- Cluster context: `kubernetes-admin@cluster.local`
- Runtime verification: pass
- Ready for goal007: yes; Pro issued `goal-007-consumer-onboarding-entitlements`

Evidence files:

- `reports/goal-006-summary.md`
- `reports/goal-006-product-contract-rollout.md`
- `reports/goal-006-product-contract-rollback.md`
- `docs/decisions/goal-006-runtime-approval.md`

## Latest Runtime State

Goal007 was implemented from ChatGPT Pro guidance and is runtime-verified
locally, pending Pro approval.

Accepted local/runtime state:

- Goal: `goal-007-consumer-onboarding-entitlements`
- Status: pending Pro approval; runtime-verified locally
- Branch: `kong-goals-foundation`
- Runtime source commit: `49b80d6`
- Evidence commit ready to approve: this document's commit
- Cluster context: `kubernetes-admin@cluster.local`
- Runtime verification: pass
- Ready for goal008: no; ask ChatGPT Pro after goal007 approval

Evidence files:

- `reports/goal-007-summary.md`
- `reports/goal-007-consumer-onboarding-rollout.md`
- `reports/goal-007-consumer-onboarding-rollback.md`
- `docs/decisions/goal-007-runtime-approval.md`

## Current Goal Source

Goal007 was issued by ChatGPT Pro after goal006 approval.

Current implementation state:

- Goal: `goal-007-consumer-onboarding-entitlements`
- Status: runtime-verified locally; pending Pro approval
- Branch: `kong-goals-foundation`
- Cluster context: `kubernetes-admin@cluster.local`
- Runtime verification: pass
- Ready for goal008: no; ask ChatGPT Pro after goal007 runtime evidence is
  committed and pushed

Goal007 scope:

- Self-service consumer contract for `branch-insights-app`
- Target product `accounts-self-service-health-v1`
- Target API `accounts`
- ACL group `banklab-accounts`
- Runtime-only key-auth and ACL credential Secrets
- Guarded apply/smoke and rollback/smoke evidence

Fresh Pro guidance for goal006:

- Small OSS/Kubernetes/GitOps increment.
- One self-service API product.
- One simulated owning team.
- Use decK-style state, OSS plugins, existing mock API, and curl proof.
- Avoid Enterprise-only and Konnect-only controls.

## Previous Pro Review

ChatGPT Pro approved `goal-005-tenancy-rbac-change-control` at evidence commit
`c032c61`.

Accepted state:

- Goal: `goal-005-tenancy-rbac-change-control`
- Status: approved; runtime-verified
- Branch: `kong-goals-foundation`
- Evidence commit approved by Pro: `c032c61`
- Cluster context: `kubernetes-admin@cluster.local`
- Runtime verification: pass
- Ready for goal006: completed after fresh Codex and Pro chats

See `soydocs/kong-bank-lab/savepoint-2026-07-09-post-goal-005.md` for the
fresh-context handoff.

## Previous Pro Review

ChatGPT Pro approved `gate-003-synthetic-api-runtime-apply-and-smoke` as a
local-only runtime gate package.

Accepted state:

- Gate: `gate-003-synthetic-api-runtime-apply-and-smoke`
- Status: pending explicit cluster mutation permission
- Branch: `kong-goals-foundation`
- Commit when Pro approved the local-only package: `37a1b7d`
- Cluster changes performed: none
- Runtime verification: not run
- Runtime approval: pending
- Ready for goal004: no
- `goal003-runtime-ready`: fails closed

Pro also accepted `post-goal-005-savepoint.md` as the programme-control rule:
after goals 004 and 005 are completed and approved, both Codex and ChatGPT Pro
must create save points, then goal 006 starts in fresh chats.

## Current Gate

Do not start goal008 until ChatGPT Pro approves
`goal-007-consumer-onboarding-entitlements`.

## Historical Goal003 Blocker

The next action is the guarded runtime apply and smoke gate for goal 003. It
requires explicit user approval for cluster mutation and an explicit target
Kubernetes context.

Current local Kubernetes context:

```text
kubernetes-admin@cluster.local
```

## Required Approval

Use this approval shape before running the cluster-mutating runtime gate. Fill
`Commit:` from the current `git rev-parse --short HEAD` output.

```text
I approve running gate-003-synthetic-api-runtime-apply-and-smoke cluster-mutating commands.

Branch: kong-goals-foundation
Commit: <current-HEAD-short-sha>
Target Kubernetes context: kubernetes-admin@cluster.local
Commands approved:
- make synthetic-api-tenant-namespaces-dry-run
- make synthetic-api-tenant-namespaces-apply
- make synthetic-api-install-dry-run
- make synthetic-api-apply
- make synthetic-api-smoke
- make synthetic-api-negative-test
- make kong-admin-exposure-test
- platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
- platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
- make evidence-goal-003
- make evidence-gate-003-synthetic-api-runtime
- make goal003-runtime-ready

Expected resources to change:
- tenant-accounts Namespace if absent
- tenant-payments Namespace if absent
- tenant-cards Namespace if absent
- tenant-customer-profile Namespace if absent
- tenant-fraud Namespace if absent
- tenant-open-banking Namespace if absent
- tenant-accounts synthetic API resources
- tenant-payments synthetic API resources
- tenant-cards synthetic API resources
- tenant-customer-profile synthetic API resources
- tenant-fraud synthetic API resources
- tenant-open-banking synthetic API resources
- synthetic API Deployments
- synthetic API Services
- synthetic API ConfigMaps
- synthetic API HTTPRoutes
- synthetic API NetworkPolicies

Expected resources not to change:
- Kong Gateway deployment
- Kong Ingress Controller deployment
- Kong GatewayClass except status reconciliation
- Kong internal and external Gateways except status reconciliation
- Kong Admin API service
- Kong CRDs
- Gateway API CRDs
- platform prereq namespaces other than the six listed tenant namespaces
- unrelated namespaces
- unrelated secrets
- unrelated workloads

Rollback command:
- make synthetic-api-rollback

Rollback note:
- Rollback removes synthetic API resources.
- Rollback intentionally leaves tenant Namespace prereqs in place.

Approval:
- approved
```

## Next Local Command Shape

After explicit approval, run the guarded gate with:

```sh
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local
platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh
```

The gate must produce runtime evidence and make `make goal003-runtime-ready`
pass before goal 004 can start.

See also `handover-2026-07-06.md` for the fresh-session restart summary and
ChatGPT Pro prompt.
