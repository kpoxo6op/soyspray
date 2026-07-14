# Kong smoke service

This isolated echo service proves that both Gateways can route traffic before
the larger sample API set is considered.

- [`deployment.yaml`](deployment.yaml) returns the marker
  `banklab-kong-smoke-ok`.
- [`service.yaml`](service.yaml) provides the upstream address.
- [`httproute-internal.yaml`](httproute-internal.yaml) and
  [`httproute-external.yaml`](httproute-external.yaml) attach the service to both
  gateways.
- [`namespace.yaml`](namespace.yaml) and [`kustomization.yaml`](kustomization.yaml)
  complete the package.

Read-only verification is available through `make smoke` from the repository
root.
