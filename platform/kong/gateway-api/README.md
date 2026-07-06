# Gateway API Baseline

Gateway API is the preferred routing surface for the bank-lab platform. Kong
Ingress Controller reconciles `GatewayClass` resources whose controller name is
`konghq.com/kic-gateway-controller`.

This goal uses unmanaged Gateway mode because Kong Gateway is installed by the
Helm baseline, not dynamically created by Kong Operator. The
`konghq.com/gatewayclass-unmanaged` annotation makes that explicit.

Two Gateway resources are declared:

- `kong-external` for external-facing lab hostnames.
- `kong-internal` for internal lab hostnames.

Both start with HTTP listeners for smoke testing. TLS hardening is deferred
until the certificate and rotation goals.
