# Synthetic API Runtime Apply And Smoke

Purpose: move goal 003 from local-only to runtime-verified only after explicit
approval, guarded apply, route smoke, negative tests, Admin API safety checks,
and evidence collection.

Required approval before mutation:

```text
I approve running gate-003-synthetic-api-runtime-apply-and-smoke cluster-mutating commands.
Branch: kong-goals-foundation
Commit:
Target Kubernetes context:
Commands approved:
- make synthetic-api-install-dry-run
- make synthetic-api-apply
- make synthetic-api-smoke
- make synthetic-api-negative-test
- make kong-admin-exposure-test
- platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
- make evidence-goal-003
- make goal003-runtime-ready
Rollback command:
- make synthetic-api-rollback
Approval:
- approved
```

Before mutation:

```bash
make validate
make validate-yaml
make validate-kustomize
make validate-synthetic-apis
make openapi-lint
make render-synthetic-apis
make synthetic-api-static-test
make synthetic-api-contract-test
make synthetic-api-smoke-plan
make test
make policy-test
make docs
make validate-synthetic-api-runtime-gate
```

After explicit approval:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
kubectl config current-context
make synthetic-api-install-dry-run
make synthetic-api-apply
make synthetic-api-smoke
make synthetic-api-negative-test
make kong-admin-exposure-test
platform/kong/synthetic-apis/scripts/collect-synthetic-api-evidence.sh
platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh
make evidence-goal-003
make evidence-gate-003-synthetic-api-runtime
make goal003-runtime-ready
```

Rollback path:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
make synthetic-api-rollback
```

Do not start goal 004 until `make goal003-runtime-ready` passes.
