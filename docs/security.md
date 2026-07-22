# Security

The controls are deliberately small and visible. They exist to show how a
request is authenticated, authorized, limited, and traced through Kong OSS.

## Request controls

Internal APIs use Key Auth and ACL plugins. The external open-banking route uses
JWT and an ACL. All routes add a correlation ID and use a Redis-backed rate
limit.

The customer and background clients read their test credentials from Kubernetes
Secrets. Secret values are not committed. KongConsumer resources refer to those
Secrets by name.

## Network boundaries

- Kong proxy traffic can reach the tenant Services.
- Tenant pods accept application traffic from Kong.
- Prometheus can scrape Kong's status port.
- Kong Ingress Controller can reach the private Admin API.
- The Admin API has no public Service or route.

Default-deny policies apply where the existing cluster networking allows them.
Every new allow rule should name the source, destination, and port.

Application namespaces enforce the Kubernetes Restricted Pod Security
standard. Workloads disable service-account token mounts, run without root or
Linux capabilities, use runtime-default seccomp, and pin container images by
digest. The Kong namespace audits and warns against the same standard because
the upstream Helm chart owns its pod settings.

## Checks

```sh
make check
make smoke
```

The smoke test covers accepted requests, missing credentials, rate limiting, and
Admin API exposure. A missing credential should return `401` or `403`. That is a
working control, not a service outage.
