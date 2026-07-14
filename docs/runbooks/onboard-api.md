# Onboard an API

1. Add the OpenAPI file under `apis/synthetic-bank` and one catalog entry.
2. Add the mock Deployment, Service, HTTPRoute, and NetworkPolicy.
3. Record the route and owning team in the API catalog.
4. Choose an existing authentication profile or define a focused new one.
5. Add positive and negative smoke cases.
6. Run `make check` and review the rendered manifests.
7. Push, deploy through Argo CD, and run `make smoke`.

Use the existing APIs as references, but keep domain-specific paths and responses
in the new package. The shared contract is ownership, routing, security, and
test coverage. The response body does not need to mimic another API.

Credentials must come from a Kubernetes Secret. Add only the Secret name and
key reference to Git.
