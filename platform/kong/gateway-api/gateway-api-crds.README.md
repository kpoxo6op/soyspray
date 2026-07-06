# Gateway API CRDs

This repo does not vendor Gateway API CRDs in goal 002.

Cluster installation requires the Gateway API standard-channel CRDs pinned in
`platform/kong/versions.yaml`.

For the current KIC `3.5.10` baseline, the supported Gateway API pin is
`v1.3.0`:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml
```

If the CRDs are missing, `make kong-cluster-smoke` must report that clearly and
the platform is not ready for route smoke testing.
