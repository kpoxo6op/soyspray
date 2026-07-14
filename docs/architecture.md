# Architecture

The lab keeps the request path small enough to inspect from end to end.

```text
customer and synthetic clients
             |
             v
        Kong proxy :80
             |
        Gateway API routes
             |
   +---------+----------+
   | tenant API pods    |
   +--------------------+

Prometheus <- Kong metrics      Loki <- Kong and client logs
     |                                      |
     +------------- Grafana ----------------+
```

## Gateway runtime

The Kong Helm release runs in `platform-kong`. Kong Ingress Controller watches
Gateway API resources and configures the data-plane pods through the private
Admin API. The Admin API has no Ingress, Gateway, LoadBalancer, or NodePort.

`kong-internal` and `kong-external` are separate Gateway resources. Most APIs
attach only to the internal gateway. Open banking uses the external gateway so
the lab can test a partner-facing route without exposing the other APIs.

## Tenant APIs

Each API has its own namespace and the same basic package:

- an OpenAPI document and catalog entry
- a small mock backend
- a ClusterIP Service and HTTPRoute
- a NetworkPolicy that accepts traffic from Kong

The catalog holds ownership and routing metadata once. Domain-specific
responses and routes stay in each API directory.

## Client traffic

The customer app gives a visible request path through Kong. Separate background
clients keep accounts, payments, customer profile, fraud, and card traffic
flowing so the dashboard remains useful between manual tests.

## Reconciliation

Ansible applies the Argo CD Application definitions. Argo CD then reconciles the
Kong release, routes, APIs, controls, customer app, traffic clients, and
dashboard. Secrets are created outside Git and referenced by name.

The `banklab-kong-crds` Application is the single owner of Kong CRDs and stays
installed while the runtime is off. The runtime chart explicitly disables CRD
installation. The dedicated AppProject permits only the resource kinds present
in the rendered lab; a chart upgrade that introduces a new kind requires an
explicit review.
