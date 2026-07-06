# NetworkPolicy Baseline

Goal 001 creates default-deny and allow-pattern examples for platform and tenant
namespaces.

## Intent

- Default deny ingress and egress in selected platform namespaces.
- Default deny ingress and egress in selected tenant namespaces.
- Allow DNS egress.
- Prepare GitOps, observability, and ingress-controller allow patterns.

No Kong-specific rule is created in goal 001.

## CNI Requirement

NetworkPolicy only enforces traffic when the cluster CNI supports it. Static
validation proves the manifests are present and parseable. Live enforcement must
be tested later with workloads.

## Recovery

If a policy blocks required traffic, revert the Git change and sync Argo CD, or
delete the specific NetworkPolicy in a controlled break-glass recovery.

