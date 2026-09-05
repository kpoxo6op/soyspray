# Headlamp

Open <https://headlamp.soyspray.vip> and select the Authentik sign-in flow to
browse the cluster. Kubernetes group permissions control access after sign-in.

The `platform` operator owns this app. The native root manages its existing
`headlamp` Application and a dedicated AppProject. It uses the same upstream chart,
release name, namespace, OIDC Secret, and cluster role bindings.

The Application reads [`values.yaml`](values.yaml) directly from this folder.
Authentik's bootstrap owns the `headlamp-oidc` Secret. Headlamp stores no durable
application data. The old Application submit role and old values path were removed
after adoption preserved the live resources and Authentik access.

Checks:

```sh
kubectl kustomize argocd
soyspray-venv/bin/python -m pytest -q tests/test_argocd_root.py tests/test_sso_headlamp.py
kubectl -n argocd get application headlamp
kubectl -n headlamp get deployment,service,ingress
```

Use [the root Ansible procedure](../../argocd/README.md) for deployment. Verify the
chart and Git revisions, then sign in and open the workload list. A successful
HTTP response alone does not prove OIDC or Kubernetes authorization.

Recovery reinstalls the chart and recreates its identity through Authentik's
bootstrap. The complete off-cluster recovery check for that identity is still
unknown. Root removal does not retire Headlamp or its shared group binding.
