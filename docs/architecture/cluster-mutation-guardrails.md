# Cluster Mutation Guardrails

Cluster mutation is any command that can create, update, delete, sync, install,
upgrade, or roll back Kubernetes resources. It requires explicit operator
permission because this repo is the source of truth and the cluster is shared
runtime state.

## Read-Only Commands

Read-only checks may inspect state with commands such as:

- `kubectl config current-context`
- `kubectl version`
- `kubectl get`
- `kubectl api-resources`
- `kubectl auth can-i`

The optional targets are `make cluster-readonly-preflight` and
`make kong-readonly-preflight`. They are not part of CI and are not part of the
required local gate.

## Mutating Commands

Mutating paths include:

- `make kong-apply`
- `make kong-rollback`
- `kubectl apply`
- `kubectl delete`
- `kubectl patch`
- `kubectl label`
- `kubectl annotate`
- `kubectl scale`
- `kubectl rollout restart`
- `helm install`
- `helm upgrade`
- `helm uninstall`
- `argocd app sync`

Mutating Make targets must call
`platform/kong/scripts/require-cluster-mutation-permission.sh` before the
mutating command.

## Required Permission

The mutation guard requires both variables:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT=<expected-kubernetes-context>
```

The guard prints the current Kubernetes context and fails if it does not match
`BANKLAB_TARGET_CONTEXT`. It never defaults to the current context silently.

## CI Boundary

CI runs only local validation. It does not run cluster smoke, optional
read-only cluster preflight, apply, rollback, install, upgrade, or Argo CD sync
commands.

## Evidence

Evidence reports must state whether any cluster-mutating commands were run. For
`gate-002-runtime-preflight`, the required answer is none.
