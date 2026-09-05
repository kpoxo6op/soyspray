# Applications

Each migrated app keeps its Argo definitions, configuration, custom source,
useful checks, and operating guide in its own folder. The native root lists
adopted apps in [its Kustomization](../argocd/kustomization.yaml).

- [Headlamp](headlamp/README.md): browse the cluster through Authentik OIDC.

Migration is incremental. The existing `kubernetes/` and
`playbooks/argocd/applications/` paths remain authoritative for apps that have not
yet been adopted. Follow [the root procedure](../argocd/README.md) and verify each
replacement before removing its old path.
