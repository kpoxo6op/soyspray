# Cluster Apply Execution Log

Status: pass

Supported states: not run, pass, fail, blocked

Reason: explicit user permission was granted in chat, the mutation guard
accepted `BANKLAB_ALLOW_CLUSTER_MUTATION=true` and
`BANKLAB_TARGET_CONTEXT=kubernetes-admin@cluster.local`, and the guarded
`make kong-apply` path applied the rendered Kong baseline.

Command:

```bash
export BANKLAB_ALLOW_CLUSTER_MUTATION=true
export BANKLAB_TARGET_CONTEXT='kubernetes-admin@cluster.local'
make kong-apply
```

Result summary:

- Gateway API CRDs applied and Established.
- `platform-kong` and `platform-kong-smoke` namespaces present.
- Kong Gateway, KIC, Gateway API resources, smoke backend, and NetworkPolicies applied.
- Runtime blockers found and fixed in repo, committed, pushed, and reapplied:
  - Gateway API CRDs vendored/applied before rendered Gateway resources.
  - KIC egress to the Kubernetes API control-plane endpoints allowed.
  - KIC egress and gateway ingress for the private Admin API on TCP 8444 allowed.
  - Kong CRDs installed by the KIC chart so controller caches stop retrying and the pod remains stable.
- Final controller and gateway pods became Ready after the declared policies were applied.

Evidence:

- Final runtime fix applied: `4cfa4fe`
- Branch: `kong-goals-foundation`
- Kubernetes context: `kubernetes-admin@cluster.local`
- Runtime evidence: `reports/kong-runtime-evidence.md`

Timestamp: 2026-07-06T21:24:18+12:00
