# Playbooks

All playbooks that customize the Kubespray cluster live here. The
supporting manifests have been flattened into purpose-driven folders so it is
clear which playbooks consume which resources:

- `argocd/` – Argo CD bootstrap assets (`config/`) and application
  definitions (`apps/`).
- `helm/` – Helm repository bootstrap manifests that get applied before Argo
  CD syncs any charts.
- `*.yml` – Task entry points that orchestrate the cluster.

Keeping the structure shallow keeps file locations intuitive and avoids the
old "everything lives in yaml/" catch-all directory.
