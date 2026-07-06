# Runtime Validation Checklist

Complete this checklist only after an approved cluster apply.

- Kong OSS baseline apply command succeeded.
- Kong pods are ready.
- KIC pods are ready.
- Gateway API resources are accepted.
- Proxy service exists.
- Proxy service type is recorded.
- LoadBalancer IP is recorded, or fallback is documented.
- Smoke backend deployment is ready.
- Smoke service has endpoints.
- Internal HTTPRoute is accepted.
- External HTTPRoute is accepted.
- Internal smoke request returns `banklab-kong-smoke-ok`.
- External smoke request returns `banklab-kong-smoke-ok`, or the LoadBalancer
  blocker is documented.
- Unknown route returns the expected failure.
- Kong Admin API is not externally exposed.
- Runtime evidence report is updated.
- Goal 003 remains blocked until all required proof is present.
