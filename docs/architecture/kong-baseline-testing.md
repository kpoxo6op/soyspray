# Kong Baseline Testing

Local tests are cluster-free and run before any apply:

```bash
make validate-kong-baseline
make render-kong-baseline
make kong-static-test
make kong-admin-exposure-test
```

`make render-kong-baseline` uses Helm to render `kong/ingress` and must not
apply resources. If Helm or chart access is unavailable, the evidence report
must record the exact blocker.

Cluster checks are opt-in:

```bash
make kong-cluster-smoke
make kong-route-smoke
```

The route smoke expects `banklab-kong-smoke-ok` from both:

- `kong-smoke.external.banklab.test`
- `kong-smoke.internal.banklab.test`

If MetalLB has not assigned a LoadBalancer IP, the route smoke script uses a
port-forward fallback.
