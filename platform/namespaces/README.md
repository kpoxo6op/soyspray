# Platform And Tenant Namespaces

These namespaces model the first ownership boundary for the Kong OSS bank lab.
Kong OSS does not provide Enterprise workspace/RBAC governance in this lab, so
Kubernetes namespaces, labels, Git ownership, Argo CD projects, and policy
checks form the prerequisite governance layer.

## Platform-Owned Namespaces

- `platform-system`: shared platform controllers and future platform runtime.
- `platform-gitops`: future Argo CD bootstrap and GitOps resources.
- `platform-security`: policy, secret-management, and security tooling.
- `platform-networking`: MetalLB, ingress, and network-level prerequisites.
- `platform-observability`: future metrics, logs, and alerting components.
- `platform-identity`: future platform identity and SSO components.

## Tenant-Owned Namespaces

- `tenant-accounts`
- `tenant-payments`
- `tenant-cards`
- `tenant-customer-profile`
- `tenant-fraud`
- `tenant-open-banking`
- `synthetic-clients`

Tenant namespaces are placeholders for future synthetic bank services and
clients. Goal 001 does not deploy workloads into them.

## Goal 001 Boundary

This goal declares namespaces and labels only. It does not install Kong, create
Gateway API resources, install Keycloak, add observability components, or deploy
synthetic APIs.

