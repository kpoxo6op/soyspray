# Kong Runtime Verification Evidence

Goal 002 may only become runtime-verified when the runtime evidence proves the
applied Kong OSS baseline works and remains safe.

Required evidence:

- Current branch.
- Current commit.
- Current Kubernetes context.
- Goal 002 version pins.
- Mutation approval present.
- Local validation passed.
- Cluster preflight passed.
- Kong install dry-run passed.
- Apply completed.
- Kong namespace exists.
- Kong pods ready.
- KIC pods ready.
- Proxy service exists.
- Proxy service type verified.
- LoadBalancer status recorded.
- GatewayClass status recorded.
- Internal Gateway status recorded.
- External Gateway status recorded.
- Smoke backend ready.
- Internal HTTPRoute status recorded.
- External HTTPRoute status recorded.
- Internal route smoke result.
- External route smoke result, or documented blocker plus fallback.
- Unknown route negative test result.
- Admin API external exposure negative test result.
- Rollback command documented.

Evidence must distinguish `not run`, `pass`, `fail`, and `blocked`.

Do not update goal 002 to runtime-verified unless all required runtime checks
pass. If external LoadBalancer smoke is blocked and only fallback smoke passes,
runtime approval remains pending unless the operator records an explicit
reduced-baseline acceptance.
