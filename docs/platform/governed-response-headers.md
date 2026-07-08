# Governed Response Headers

Goal009 adds a reversible Kong OSS response-header control to the existing
accounts API path.

The source contract is rendered by:

- `scripts/render_goal009_response_headers.py`

The rendered runtime resources are:

- `configuration.konghq.com/v1/KongPlugin` in `tenant-accounts`
- `gateway.networking.k8s.io/v1/HTTPRoute` annotation patch for
  `tenant-accounts/banklab-accounts`

The plugin is `response-transformer`, which is allowed by the Goal008
governance policy. It adds only these response headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `X-BankLab-Response-Policy: goal009`

The route annotation preserves the existing Goal004 plugin chain and appends
`banklab-goal009-security-headers`. It does not change authentication,
authorization, rate limiting, routing, services, request bodies, request
headers, upstream application code, TLS, or the Kong Admin API.

Rollback reapplies the stable accounts route annotation and deletes the
Goal009 `KongPlugin`. Runtime rollback evidence must prove the response policy
marker is absent and the existing Goal004 positive, negative, rate-limit, and
Admin API exposure safety checks still pass.
