# Goal008 Governance Policy Rollback

Use this runbook when the Kong governance admission policy must be removed.

## Scope

Rollback removes only:

- `ValidatingAdmissionPolicyBinding/banklab-kong-plugin-governance`
- `ValidatingAdmissionPolicy/banklab-kong-plugin-governance`

Rollback does not remove or mutate existing KongPlugin, KongConsumer, HTTPRoute,
Gateway, Secret, or synthetic API resources.

## Guard

Before rollback, set:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local
```

Verify the active context:

```bash
kubectl config current-context
```

It must match `BANKLAB_TARGET_CONTEXT`.

## Rollback

```bash
make goal008-governance-policy-rollback-and-smoke
```

## Acceptance

Rollback is accepted only when:

- the policy binding is absent
- the policy is absent
- the unsafe `request-transformer` fixture becomes server-dry-run admissible
- existing goal004 runtime smoke still passes in the `goal008-runtime-ready`
  sequence
- Kong Admin API safety remains passing

Evidence is written to `reports/goal-008-governance-policy-rollback.md`.
