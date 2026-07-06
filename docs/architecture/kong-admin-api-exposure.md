# Kong Admin API Exposure

Rule: Kong Admin API must not be externally reachable.

Goal 002 enforces that rule with source checks and tests:

- Admin service type must be `ClusterIP`.
- Admin ingress must be disabled.
- Gateway and HTTPRoute manifests must not route to Admin API.
- Kong Manager is disabled and is not a platform control plane.
- Portal and Portal API are disabled.

KIC may need internal Admin API access to configure Kong. That path is private
inside the cluster and must not be exposed with LoadBalancer, NodePort, Ingress,
Gateway, or HTTPRoute.

Run:

```bash
make kong-admin-exposure-test
```
