# Prometheus

Prometheus and Grafana

## Helm Inflate

Uses Helm Inflate to apply values and custom resources.

looks like it fully works in pihole app - custom configmaps and values are
applied automatically.

custom resources seem to work in prometheus

`playbooks/yaml/argocd-apps/prometheus/values.yaml` are not applied in prometheus
