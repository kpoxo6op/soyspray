# Kong Smoke Backend

The smoke backend proves the Kong Gateway baseline can route traffic through
Gateway API. It is platform-owned and disposable. It is not a banking API and
must not become part of tenant onboarding.

Expected hostnames:

- `kong-smoke.external.banklab.test`
- `kong-smoke.internal.banklab.test`

If MetalLB is not available, route smoke testing may use a port-forward
fallback.
