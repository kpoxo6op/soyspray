# Disposable monitoring configuration

This Argo child owns the Soyspray Grafana dashboard ConfigMaps and custom
PrometheusRule objects in `monitoring`. Edit the JSON in `dashboards/` or the
rules in `alerts/`, then merge to `main`. The child updates stable dashboard
ConfigMap names and prunes removed files, so a Git revert also removes a
temporary dashboard or rule. The Prometheus stack and CRDs have separate,
non-pruning owners.

Run `make check APP=prometheus`, `make diff APP=prometheus`, and `make go`
before merging. Check `kubectl -n argocd get application prometheus-config`
after delivery. The AppProject permits only ConfigMaps and PrometheusRules in
`monitoring`; it cannot manage cluster resources, Secrets, or volumes.

The ConfigMaps are Grafana sidecar inputs, not Grafana's database backup.
Prometheus rules describe alert conditions; a resolved alert by itself does
not prove that an application recovered.
