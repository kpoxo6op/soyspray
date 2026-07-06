# Kong OSS Baseline

This directory contains the goal-002 Kong OSS baseline. It defines the first
runtime gateway layer, but it does not apply anything to the cluster by default.

The baseline is intentionally narrow:

- Kong Gateway OSS image `kong:3.9.3`.
- Kong Ingress Controller image `kong/kubernetes-ingress-controller:3.5.10`.
- Kong `kong/ingress` Helm chart `0.24.0`.
- Gateway API standard channel `v1.3.0`.
- DB-less Kong mode.
- Gateway API HTTP smoke routes only.
- Admin API private to the cluster.
- Proxy Service intended for MetalLB `LoadBalancer`.

Kong has a dedicated `platform-kong` namespace so gateway runtime policy,
rollout, and rollback can be handled independently from prerequisite platform
services. The smoke backend uses `platform-kong-smoke` and is platform-owned; it
is not a synthetic banking API.

Local validation is the source of truth until the user explicitly permits a
cluster apply. Do not claim Kong is installed unless `make kong-apply`,
`make kong-cluster-smoke`, and `make kong-route-smoke` have actually passed.
