# Admin API Exposure Results

Status: pass

Supported states: not run, pass, fail, blocked

Reason: Admin API remains ClusterIP-only and was not reachable through the
LoadBalancer; admin-like HTTP host routing returned the normal Kong 404.

Command:

```bash
make kong-admin-exposure-test
kubectl -n platform-kong get svc banklab-kong-gateway-admin banklab-kong-gateway-proxy -o wide
curl --connect-timeout 3 --max-time 5 http://192.168.20.22:8444/status
curl --resolve "admin.external.banklab.test:80:192.168.20.22" \
  http://admin.external.banklab.test/
```

Result summary:

- Static Admin exposure validation passed.
- `banklab-kong-gateway-admin` is `ClusterIP` with no external IP.
- `banklab-kong-gateway-proxy` exposes only HTTP port 80 through `192.168.20.22`.
- `http://192.168.20.22:8444/status` failed to connect.
- `admin.external.banklab.test` over port 80 returned HTTP `404`, not Admin API content.
- Runtime-created secrets were limited to KIC webhook TLS material:
  `banklab-kong-controller-validation-webhook-ca-keypair` and
  `banklab-kong-controller-validation-webhook-keypair`.

Evidence:

- Runtime evidence: `reports/kong-runtime-evidence.md`

Timestamp: 2026-07-06T21:24:18+12:00
