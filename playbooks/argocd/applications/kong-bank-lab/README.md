# Kong bank lab Argo CD applications

This folder splits the lab into small Argo CD applications with clear ownership
and shutdown behaviour.

## Lifecycle

`banklab-kong-project.yaml` defines the allowed repositories and destinations.
`banklab-kong-crds-application.yaml` stays present so shared CRDs are not
repeatedly installed and deleted. The other eight `*-application.yaml` files are
the optional runtime removed when the lab is parked.

| Runtime area | Application file |
| --- | --- |
| Kong chart | [`banklab-kong-application.yaml`](banklab-kong-application.yaml) |
| Gateway API resources | [`banklab-kong-gateway-api-application.yaml`](banklab-kong-gateway-api-application.yaml) |
| Smoke service | [`banklab-kong-smoke-application.yaml`](banklab-kong-smoke-application.yaml) |
| Sample APIs | [`synthetic-bank-apis-application.yaml`](synthetic-bank-apis-application.yaml) |
| Security controls | [`banklab-kong-security-controls-application.yaml`](banklab-kong-security-controls-application.yaml) |
| Demo and traffic | [`banklab-customer-traffic-application.yaml`](banklab-customer-traffic-application.yaml) |
| Metrics and dashboard | [`banklab-kong-operator-dashboard-application.yaml`](banklab-kong-operator-dashboard-application.yaml) |
| Operator guide | [`banklab-docs-application.yaml`](banklab-docs-application.yaml) |

The Ansible role in
[`../../../../roles/apps/kong-bank-lab/`](../../../../roles/apps/kong-bank-lab/)
applies or removes these definitions. The default state is off.
