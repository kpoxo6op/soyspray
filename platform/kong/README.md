# Kong platform

This folder defines the shared Kong data plane and its supporting Gateway API,
network, smoke-test, and Helm configuration.

| Folder | Purpose |
| --- | --- |
| [`helm/`](helm/) | Values for the pinned Kong chart |
| [`gateway-api/`](gateway-api/) | GatewayClass plus internal and external Gateways |
| [`network-policies/`](network-policies/) | Default-deny and required platform paths |
| [`smoke/`](smoke/) | Small upstream used for gateway verification |

[`namespace.yaml`](namespace.yaml) creates the platform namespace and
[`kustomization.yaml`](kustomization.yaml) renders the repository-managed
resources. Argo CD application definitions live in
[`../../playbooks/argocd/applications/kong-bank-lab/`](../../playbooks/argocd/applications/kong-bank-lab/).
