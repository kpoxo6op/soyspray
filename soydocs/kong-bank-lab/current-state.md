# Kong Bank Lab Current State

Updated: 2026-07-06

## Branch

- Branch: `kong-goals-foundation`
- Latest pushed checkpoint before this handover: `fadc0d8`
- Before approval, confirm the current commit with `git rev-parse --short HEAD`
  and put that value in the approval block.

## Latest Pro Review

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

## Current Blocker

Do not start `goal-004-auth-rate-limit-security` yet.

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
- unrelated namespaces
- unrelated secrets
- unrelated workloads

Rollback command:
- make synthetic-api-rollback

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
