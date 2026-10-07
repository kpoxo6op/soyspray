# Argo CD access and ownership

Argo manages its pinned runtime; Ansible owns controller configuration and
private inputs. The server uses TLS and its Ingress sends HTTPS to port 443.
Use `make argo-login` and the [current Argo guide](../apps/argocd/README.md).
Merge CI-green source PRs; Applications follow `main`. The old top-level wrapper
and manual insecure-server procedure are retired.

Read native state with `argocd app list` and `argocd app get longhorn`.
Do not apply old bootstrap or direct workload-sync instructions for routine
changes. See [everyday operations](../docs/operations.md).
