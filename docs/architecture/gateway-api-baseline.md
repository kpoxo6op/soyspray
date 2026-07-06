# Gateway API Baseline

Kong routes are modeled with Gateway API, not the Admin API. Goal 002 declares:

- `GatewayClass/kong`
- `Gateway/platform-kong/kong-external`
- `Gateway/platform-kong/kong-internal`
- Two smoke `HTTPRoute` resources in `platform-kong-smoke`

The default controller name is `konghq.com/kic-gateway-controller`. The
GatewayClass is marked unmanaged because this repo installs Kong Gateway
separately through Helm; Kong Operator is not part of this goal.

Gateway API is pinned to `v1.3.0` because Kong's KIC compatibility table shows
KIC `3.5.x` supports Gateway API `1.3`, `1.2`, `1.1`, and `1.0`.

The internal and external Gateways have separate hostnames so future tenant
boundaries can attach routes intentionally. Both use HTTP listeners for smoke
testing. TLS is deferred to a later certificate and rotation goal.
