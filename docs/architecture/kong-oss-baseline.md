# Kong OSS Baseline

Goal 002 introduces the first Kong runtime layer. It is repository-first: local
validation and rendered manifests are produced before any cluster apply.

Selected versions:

- Kong Gateway OSS image: `kong:3.9.3`
- Kong Ingress Controller image: `kong/kubernetes-ingress-controller:3.5.10`
- Helm chart: `kong/ingress` `0.24.0`
- Gateway API standard channel: `v1.3.0`

The baseline uses DB-less mode. PostgreSQL is deliberately not introduced yet
because KIC owns declarative configuration through Kubernetes resources.

The proxy Service is a `LoadBalancer` intended for MetalLB. The Admin API is
ClusterIP-only and is not a human control plane. Kong Manager and Portal are
disabled.

Sources used for version and controller-name choices:

- Kong chart repository: `https://charts.konghq.com`
- Kong Gateway API controller name: `https://developer.konghq.com/kubernetes-ingress-controller/gateway-api/`
- Gateway API release: `https://github.com/kubernetes-sigs/gateway-api/releases/tag/v1.3.0`
- Kong KIC compatibility: `https://developer.konghq.com/kubernetes-ingress-controller/version-compatibility/`
- KIC release: `https://github.com/Kong/kubernetes-ingress-controller/releases/tag/v3.5.10`
