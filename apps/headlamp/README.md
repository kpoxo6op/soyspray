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

Normal commands:

```sh
make check APP=headlamp
make status APP=headlamp FORMAT=json
make diff APP=headlamp
```

Merge the pull request to deploy through the [native root](../../argocd).
The chart is pinned to the existing `0.35.0` release. Diff compares the clean,
pushed Git commit and this exact chart through native Argo revision overrides.
Verify the chart and `main` Git revision, then sign in and open the workload list. A successful
HTTP response alone does not prove OIDC or Kubernetes authorization.

Recovery reinstalls the chart and recreates its identity through Authentik's
bootstrap. The complete off-cluster recovery check for that identity is still
unknown. Root removal does not retire Headlamp or its shared group binding.

`smoke` and `restore-check` remain unknown until maintained commands cover the
authenticated journey and Authentik identity recovery. Deployment does not rotate
or recreate the OIDC Secret or change Kubernetes group access.
