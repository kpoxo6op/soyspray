# Kong Runtime Smoke Checklist

Run this only after the Kong baseline is explicitly applied.

## Resource Checks

- `platform-kong` namespace exists.
- Kong pods are ready.
- KIC pods are ready.
- Proxy service exists.
- Proxy service type is recorded.
- LoadBalancer IP is recorded, or port-forward fallback is recorded.
- `GatewayClass/kong` status is accepted.
- Internal Gateway status is accepted.
- External Gateway status is accepted.
- `platform-kong-smoke` namespace exists.
- Smoke backend deployment and service are ready.
- Internal and external HTTPRoutes are accepted.

## Request Checks

- Internal smoke request returns `banklab-kong-smoke-ok`.
- External smoke request returns `banklab-kong-smoke-ok`, or the LoadBalancer
  blocker is recorded.
- Unknown route returns the expected failure.
- Kong Admin API is not reachable through any external route or LoadBalancer
  path.

Record every result in the runtime evidence report before unblocking goal 003.
