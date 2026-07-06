# Kong Bank Lab Current State

Updated: 2026-07-06

## Branch

- Branch: `kong-goals-foundation`
- Latest pushed commit before this note: `37a1b7d`

## Latest Pro Review

ChatGPT Pro approved `gate-003-synthetic-api-runtime-apply-and-smoke` as a
local-only runtime gate package.

Accepted state:

- Gate: `gate-003-synthetic-api-runtime-apply-and-smoke`
- Status: pending explicit cluster mutation permission
- Branch: `kong-goals-foundation`
- Commit: `37a1b7d`
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

## Approval Phrase

Use this exact approval shape before running the cluster-mutating runtime gate:

```text
I approve running gate-003-synthetic-api-runtime-apply-and-smoke cluster-mutating commands.
Target Kubernetes context: kubernetes-admin@cluster.local
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
