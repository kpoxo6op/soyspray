# Platform Prerequisites

Goal 001 prepares the Kubernetes prerequisite layer for the Kong OSS bank lab.

The layer includes namespaces, staged Argo CD structure, MetalLB examples,
cert-manager examples, SOPS/age structure, baseline NetworkPolicy, local
validation, and opt-in cluster checks.

It does not install Kong, install Keycloak, deploy observability tools, create
synthetic APIs, or apply resources to the cluster automatically.

## Namespace Model

Platform namespaces are owned by platform, security, networking, identity, and
observability teams. Tenant namespaces model future bank API domains such as
accounts, payments, cards, customer profile, fraud, and open banking.

All namespaces carry ownership, environment, data classification, and
platform-layer labels so validation and policy checks can reason about them.

## Validation

Local validation must pass without a cluster:

```sh
make validate-prereqs
```

Cluster validation is explicit and opt-in:

```sh
make cluster-prereq-smoke
```

## Known Limitations

These manifests are prerequisites only. They prove structure and intent, not
live cluster enforcement. NetworkPolicy enforcement depends on the cluster CNI.

