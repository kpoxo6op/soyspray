# Kong Runtime Apply Plan

Generated at: 2026-07-06T20:45:59+12:00

Branch: kong-goals-foundation

Commit: 15bff35

This plan is generated from repository files only. It does not query the
cluster and it does not mutate the cluster.

## Version Locks

- Kong Gateway: `kong:3.9.3`
- Kong mode: `dbless`
- Kong Enterprise enabled: `False`
- KIC: `kong/kubernetes-ingress-controller:3.5.10`
- Gateway API: `v1.3.0`
- Helm chart: `kong/ingress 0.24.0`

## Gateway API CRDs

- `platform/kong/gateway-api/crds/standard-install.yaml`
- Applied first by the guarded `make kong-apply` path.
- Rollback does not remove Gateway API CRDs.

## Expected Namespaces

- `platform-kong`
- `platform-kong-smoke`

## Expected Gateway API Resources

- `Gateway API standard CRDs from platform/kong/gateway-api/crds/standard-install.yaml`
- `GatewayClass/kong`
- `Gateway/platform-kong/kong-external`
- `Gateway/platform-kong/kong-internal`
- `HTTPRoute/platform-kong-smoke/kong-smoke-external`
- `HTTPRoute/platform-kong-smoke/kong-smoke-internal`

## Expected Smoke Resources

- `Namespace/platform-kong-smoke`
- `Deployment/platform-kong-smoke/kong-smoke-backend`
- `Service/platform-kong-smoke/kong-smoke-backend`

## Expected NetworkPolicy Resources

- `NetworkPolicy/platform-kong/kong-default-deny`
- `NetworkPolicy/platform-kong/kong-allow-dns`
- `NetworkPolicy/platform-kong/kong-allow-kube-api-placeholder`
- `NetworkPolicy/platform-kong/kong-allow-proxy-ingress`
- `NetworkPolicy/platform-kong/kong-allow-smoke-upstream`

## Expected Argo CD Templates

- `platform/kong/argocd/kong-baseline-app.yaml`
- `platform/kong/argocd/kong-gateway-api-app.yaml`
- `platform/kong/argocd/kong-smoke-app.yaml`
- `platform/gitops/app-of-apps/kong-baseline-app.yaml`

## Admin API Exposure Model

The Kong Admin API must remain private. Static validation requires the Admin
service to be ClusterIP-only and rejects Ingress, Gateway, or HTTPRoute paths
that expose Admin API traffic externally.

## Explicit Cluster Apply Commands

Do not run these commands without explicit user permission and the mutation
guard variables:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-apply
```

Rollback command:

```bash
BANKLAB_ALLOW_CLUSTER_MUTATION=true BANKLAB_TARGET_CONTEXT=<expected-context> make kong-rollback
```

## Known Runtime Dependencies

- Kubernetes API access and the expected context must be confirmed.
- Gateway API CRDs must exist before Gateway resources can be accepted.
- MetalLB or another LoadBalancer implementation is needed for external proxy
  service IP assignment.
- NetworkPolicy behavior depends on the live CNI.
- Route smoke tests require an applied Kong baseline.

## Runtime Proof Boundary

This plan does not prove runtime success. Runtime success requires explicit
cluster apply and smoke validation in a later approved gate.
