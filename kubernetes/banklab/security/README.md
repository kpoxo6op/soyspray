# Bank lab security controls

This package connects API routes to Kong authentication, authorization,
rate-limiting, consumer, and credential resources. It also provides the network
paths required by those controls.

- [`security-controls.yaml`](security-controls.yaml) contains the shared Redis
  service and Kong policy resources.
- [`kong-allow-api-upstreams.yaml`](kong-allow-api-upstreams.yaml) permits Kong
  to reach the API namespaces.
- [`kustomization.yaml`](kustomization.yaml) is the package entry point.

The API catalog at
[`../../../apis/synthetic-bank/api-catalog.yaml`](../../../apis/synthetic-bank/api-catalog.yaml)
records the intended policy profile for each route.
