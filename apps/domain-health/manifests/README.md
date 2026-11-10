# Domain check workload

The Deployment and Service preserve the existing names, ports, selectors, probes,
resources, and Secret references.

Render with `kubectl kustomize apps/domain-health` from the repo root. Use the
[app commands](..) for deployment and verify the Prometheus scrape and
recent check results afterward. No persistent volume belongs to this app.
