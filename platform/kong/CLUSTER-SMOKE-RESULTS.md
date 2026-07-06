# Cluster Smoke Results

Status: pass

Supported states: not run, pass, fail, blocked

Reason: Kong runtime cluster checks passed after the guarded apply.

Command:

```bash
make kong-cluster-smoke
kubectl -n platform-kong wait --for=condition=Ready pod -l app.kubernetes.io/name=controller --timeout=420s
kubectl -n platform-kong wait --for=condition=Ready pod -l app.kubernetes.io/name=gateway --timeout=240s
```

Result summary:

- `make kong-cluster-smoke` returned `Kong cluster smoke passed.`
- Controller pod Ready: `banklab-kong-controller-6b67f44db8-rhs5j`.
- Gateway pods Ready: `banklab-kong-gateway-75b48d447c-wbskb`, `banklab-kong-gateway-75b48d447c-xgf87`.
- `GatewayClass/kong` Accepted=True.
- `Gateway/kong-external` Programmed=True with address `192.168.20.22`.
- `Gateway/kong-internal` Programmed=True with address `192.168.20.22`.
- KIC stayed Running after Kong CRDs were installed; `kubectl logs --since=5m`
  returned no new controller log lines at `2026-07-06T21:24:18+12:00`.

Evidence:

- Runtime evidence: `reports/kong-runtime-evidence.md`

Timestamp: 2026-07-06T21:24:18+12:00
