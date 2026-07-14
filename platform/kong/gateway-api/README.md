# Kong Gateway API resources

This package gives Kong an internal and an external traffic boundary.

- [`gatewayclass-kong.yaml`](gatewayclass-kong.yaml) connects Gateway API to the
  Kong controller.
- [`gateway-internal.yaml`](gateway-internal.yaml) accepts internal bank-lab
  hostnames.
- [`gateway-external.yaml`](gateway-external.yaml) accepts external bank-lab
  hostnames.
- [`kustomization.yaml`](kustomization.yaml) is the package entry point.

Application routes attach to one of these Gateways from their tenant namespace.
