# Helm bootstrap manifests

This folder contains Kubernetes resources that prepare Helm-based
applications before Argo CD begins reconciling charts. Each file is referenced
explicitly from the playbooks (e.g. `deploy-argocd-apps.yml`) using
`{{ playbook_dir }}/helm/...`, so it is clear where supporting manifests live.
