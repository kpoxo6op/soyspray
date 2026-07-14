# Grafana dashboards

[`kong-bank-lab-operator-overview.json`](kong-bank-lab-operator-overview.json)
is the provisioned Grafana dashboard for gateway health, request outcomes,
latency, and policy behaviour.

The parent [`kustomization.yaml`](../kustomization.yaml) packages this JSON into
a labelled ConfigMap discovered by the existing Grafana sidecar.
