# Route Smoke Results

Status: pass

Supported states: not run, pass, fail, blocked

Reason: positive internal/external smoke routes returned the expected response
through the MetalLB LoadBalancer address, and an unknown host returned the
expected Kong 404.

Command:

```bash
make kong-route-smoke
curl --resolve "kong-unknown.external.banklab.test:80:192.168.20.22" \
  http://kong-unknown.external.banklab.test/
```

Result summary:

- External route output: `banklab-kong-smoke-ok`
- Internal route output: `banklab-kong-smoke-ok`
- Unknown route HTTP status: `404`
- Unknown route response: `no Route matched with those values`
- Proxy LoadBalancer IP: `192.168.20.22`

Evidence:

- Runtime evidence: `reports/kong-runtime-evidence.md`

Timestamp: 2026-07-06T21:24:18+12:00
