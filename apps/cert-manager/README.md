# Cert-manager controllers

Argo CD owns the existing cert-manager controller, webhook, cainjector and CRDs.
The jetstack chart and images stay at `v1.17.1`, with release and namespace
`cert-manager`. The separate [certificate configuration](../cert-manager-config)
Application owns issuers, certificates and reflection. This chart cannot manage
Secrets, Issuers or Certificates through its AppProject.

```sh
make check APP=cert-manager
make diff APP=cert-manager
kubectl -n argocd get application cert-manager
kubectl get certificates -A
kubectl get clusterissuers
```

The comparison requires an already adopted Application and a clean pushed commit.
For initial adoption, render the exact chart and use a server-side dry run;
verify immutable selectors, preserved controller arguments, unchanged credential
and certificate identities, admission and CA injection, and trusted ingress TLS.
The Helm startup check is disabled because admission is verified directly.

Values preserve the existing DNS-01 arguments, pod DNS settings and leader
namespace. Null solver-image and concurrency overrides retain the binary's
existing defaults and exact controller arguments. Controllers may roll once to
adopt chart metadata; no certificate renewal or Secret rotation is requested.

Automated pruning and empty-source deletion retain their false defaults; the
explicit `Prune=false,Delete=false` sync options prevent resource retirement.
Cascading Application deletion is disabled. CRDs use
`crds.keep: true`. Argo respects the CA bundles maintained by cainjector.
Server-side diff asks the API server to compare the live schema, avoiding the
older Argo controller schema for Kubernetes status fields.
After verified adoption, disable the Kubespray cert-manager addon before using
upstream Kubespray. Never run its enabled addon against this namespace.

Rollback changes chart values through a CI-green PR. Keep the Application,
namespace, CRDs, issuers, certificates and Secrets during rollback. Returning
controller ownership to the old fork requires a deliberate reviewed transition;
leave its cert-manager namespace deletion protection intact.
