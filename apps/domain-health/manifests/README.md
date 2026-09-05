# Domain check workload

The Deployment and Service preserve the existing names, ports, selectors, probes,
resources, and Secret references. The app-level Kustomize file supplies the
existing exporter ConfigMap from the frozen `legacy-exporter.py` during the
initial image transition. Keep that file unchanged until the tested image is
promoted and verified, then remove it.

Render with `kubectl kustomize apps/domain-health` from the repo root. Use the
[app commands](../README.md) for deployment and verify the Prometheus scrape and
recent check results afterward. No persistent volume belongs to this app.
