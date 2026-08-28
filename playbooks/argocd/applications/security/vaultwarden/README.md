# Vaultwarden Argo CD resources

[`vaultwarden-project.yaml`](vaultwarden-project.yaml) limits Vaultwarden to its
repository and namespace.
[`vaultwarden-application.yaml`](vaultwarden-application.yaml) deploys the
[`kubernetes/vaultwarden`](../../../../../kubernetes/vaultwarden/README.md)
package.

Keep the committed `targetRevision` at `HEAD`. Test a pushed branch through the
Ansible role:

```bash
make vaultwarden VAULTWARDEN_REVISION="$(git branch --show-current)"
```

Check the result with:

```bash
kubectl -n argocd get application vaultwarden
```
