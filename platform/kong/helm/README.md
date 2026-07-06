# Kong Helm Baseline

The baseline uses `kong/ingress` `0.24.0` from `https://charts.konghq.com`.
That meta chart deploys a split Kong Ingress Controller release and a Kong
Gateway release using DB-less mode.

The values file keeps local CI cluster-free. Rendering is available through:

```bash
make render-kong-baseline
```

Rendering may need Helm and chart repository access. It must never apply
resources to the cluster.
