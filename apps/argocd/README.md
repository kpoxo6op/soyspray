# Argo CD runtime

The `argocd` Application manages Argo CD itself using the exact upstream
v2.14.5 installation manifests. Kubespray must keep `argocd_enabled: false`.
The runtime has no application PVC; its existing Secrets remain private inputs.

## Ownership

Argo owns the seven workloads, their service accounts, RBAC, CRDs, network
policies and standard Services. Adoption preserves pod templates and images.
Every rendered resource carries `Prune=false,Delete=false`; the Application
has no cascading finalizer and uses server-side apply and comparison.

All Secrets and ConfigMaps are excluded. Ansible owns controller settings in
`playbooks/argocd/config/` and Authentik owns its OIDC input through
`apps/authentik/bootstrap/`. GPG, repository trust and notification configuration
remain deliberate Ansible inputs, preserving existing content. The customized
`argocd-server` Service and Ingress remain in `playbooks/argocd/config/`.
No upstream Secret, including `argocd-secret`, is rendered or adopted.

## Commands and upgrades

```sh
make check APP=argocd
kubectl kustomize apps/argocd/manifests
make diff APP=argocd
kubectl -n argocd get applications,deployments,statefulsets,pods
```

An Argo upgrade changes the pinned upstream version through a CI-green PR.
Compare the rendered resources and server dry runs first, preserving private
inputs, controller configuration and custom ingress/service settings. Verify
the root, this Application and every other Application after merge.
Kubespray upgrades change its upstream tag and use full `upgrade-cluster.yml`
with the existing complete inventory, OIDC variables and snapshot/health gates.

## Limits and rollback

Native health does not prove SSO or browser access. Use kubectl as break-glass.
Keep root pruning disabled. Revert through a CI-green PR without deleting the
Application, namespace, CRDs or credentials. Never re-enable Kubespray's Argo
addon as a rollback: it rewrites the admin credential metadata.
