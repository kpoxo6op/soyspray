# Kong Runtime Apply Checklist

Do not use this checklist as approval by itself. Fill
`platform/kong/CLUSTER-APPLY-REQUEST.md` and get explicit approval before any
cluster-mutating command.

## Preconditions

- User approval is explicit and current.
- Branch and commit are recorded.
- `BANKLAB_TARGET_CONTEXT` is the expected Kubernetes context.
- `BANKLAB_ALLOW_CLUSTER_MUTATION=true` is set only for the approved run.
- Gateway API CRDs are present or their installation path is separately
  approved.
- MetalLB is ready if the LoadBalancer path is expected.
- cert-manager status is known if TLS examples are used.
- Argo CD status is known if GitOps sync is used.
- `reports/kong-runtime-apply-plan.md` is current.

## Expected Resources To Change

- `platform-kong` namespace and Kong runtime resources.
- `platform-kong-smoke` namespace and smoke backend resources.
- Gateway API resources for the internal and external smoke paths.
- NetworkPolicy resources under `platform/kong/network-policies`.

## Expected Resources Not To Change

- Business API namespaces and workloads.
- Real secrets.
- Cluster identity or SSO systems.
- Observability stack.
- Kong Enterprise resources.

## Command Path

The approved direct apply path is:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-apply
```

Rollback path:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-rollback
```

Collect command output, current context, pod readiness, Gateway status, service
status, route smoke results, and Admin API exposure negative-test results.
