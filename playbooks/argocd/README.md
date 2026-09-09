# ArgoCD

Argo CD bootstrap and controller configuration.

## Structure

### playbooks/
Ansible playbooks for bootstrapping and configuring Argo CD itself.

### config/
ArgoCD controller configuration files and configuration playbooks.

Application manifests, checks, bootstrap inputs, and operating guides live
under `apps/NAME/`. The native catalog is `argocd/catalog/`. Applications
follow GitHub `main`; Ansible does not submit or deploy application workloads.
