# ArgoCD

Argo CD bootstrap and controller configuration.

## Structure

### playbooks/
Ansible playbooks for bootstrapping and configuring Argo CD itself.

The running installation belongs to the pinned, non-pruning self-management
Application under [apps/argocd](../../apps/argocd/README.md). Kubespray's Argo
addon stays disabled. Ansible owns configuration, custom Service/Ingress and
private OIDC inputs. The server keeps TLS enabled and its Ingress uses HTTPS
port 443. The local admin credential is a separate private Vault input; use
the [guarded security operations](../operations/security/README.md).

### config/
ArgoCD controller configuration files and configuration playbooks.

Application manifests, checks, bootstrap inputs, and operating guides live
under `apps/NAME/`. The native catalog is `argocd/catalog/`. Applications
follow GitHub `main`; Ansible does not submit or deploy application workloads.
