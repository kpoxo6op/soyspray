# Kong Cluster Apply And Smoke

This runbook is for `gate-002-cluster-apply-and-smoke`. It has two phases:
local validation before permission, and runtime execution after explicit
cluster mutation permission.

## Local Validation Before Permission

Run these from the repository root:

```bash
make validate
make validate-yaml
make validate-kustomize
make validate-prereqs
make validate-kong-baseline
make render-kong-baseline
make kong-static-test
make kong-admin-exposure-test
make runtime-preflight-local
make kong-apply-plan
make mutation-guard-test
make validate-cluster-apply-gate
make test
make policy-test
make docs
make evidence-gate-002-cluster-apply-and-smoke
```

These commands prove that the repo, manifests, Kong baseline, runtime preflight
package, mutation guardrails, tests, docs, and pending evidence contract are
ready without Kubernetes access.

## Permission Boundary

Do not continue until the operator explicitly approves cluster mutation and
provides the expected Kubernetes context.

Required exports:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
```

Verify the live context:

```bash
kubectl config current-context
```

The output must match `BANKLAB_TARGET_CONTEXT`.

## Runtime Sequence After Permission

Run:

```bash
make cluster-readonly-preflight
make kong-readonly-preflight
make cluster-smoke
make cluster-prereq-smoke
make kong-install-dry-run
make kong-apply
make kong-cluster-smoke
make kong-route-smoke
make kong-admin-exposure-test
platform/kong/scripts/collect-kong-runtime-evidence.sh
make evidence-goal-002
make evidence-gate-002-cluster-apply-and-smoke
make goal002-runtime-ready
```

The read-only preflights show the current context, prerequisite state, and
whether Kong already exists. The dry-run proves the API server will accept the
rendered resources. `make kong-apply` is the guarded mutation. The smoke checks
prove Kong, KIC, Gateway API resources, routes, and Admin API exposure behavior.

If any step fails, stop and use `docs/runbooks/kong-cluster-apply-failure.md`.
