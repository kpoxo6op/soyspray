# Disposable monitoring configuration

This folder stages Soyspray Grafana dashboards and custom Prometheus rules for
a separate, narrowly scoped Argo child. The first migration change releases
these objects from the non-pruning stack Application. They remain live while
that child is created in the next reviewed change. Do not add or remove rules
between these two migration changes.

Run `make check APP=prometheus`, `make diff APP=prometheus`, and `make go`
before merging. The next change will add an AppProject permitting only
ConfigMaps and PrometheusRules in `monitoring`.

The ConfigMaps are Grafana sidecar inputs, not Grafana's database backup.
Prometheus rules describe alert conditions; a resolved alert by itself does
not prove that an application recovered.
