# Operations

## Daily check

```sh
make status
make smoke
```

Start in Argo CD. Every bank-lab Application should be `Synced` and `Healthy`.
Then open the Grafana gateway dashboard.

## Read the dashboard

The top row answers four questions:

1. Is Kong receiving traffic?
2. Are server errors increasing?
3. Is latency changing?
4. Are both gateway pods ready?

Rate-limit responses are shown separately from server errors. The background
clients intentionally produce some rejected requests, so a steady low 4xx rate
is expected. A 5xx spike or missing traffic needs investigation.

Use route and client panels to narrow the problem. Open the recent error logs
only after the overview shows which path or status changed.

## First response

```sh
kubectl -n platform-kong get pods
kubectl get httproutes -A
kubectl -n argocd get applications.argoproj.io
```

Do not fix drift with an imperative cluster write. Find the owning manifest,
push the correction, and let Argo reconcile it. Use the [rollback
runbook](runbooks/rollback.md) when the last change caused the fault.

## Publish documentation

Edit `docs/` or `mkdocs.yml`, then commit and push the change. The
`banklab-docs` workload checks the tracked Git revision every minute and builds
the static site when it changes. Nginx keeps serving the last successful build
at [banklab-docs.soyspray.vip](https://banklab-docs.soyspray.vip).

`make docs` is a local validation command. It is not a publishing step.
