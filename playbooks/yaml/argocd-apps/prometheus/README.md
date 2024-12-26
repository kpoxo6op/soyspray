# Prometheus and Grafana Setup

This setup uses Prometheus to scrape metrics and Grafana to visualize them.

## Prometheus Configuration

Prometheus uses a Kubernetes Secret to define custom scrape jobs. This is
referenced in the Prometheus Helm chart's `values.yaml`.

A Secret named `additional-scrape-configs` in the monitoring namespace stores
these scrape job configurations.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: additional-scrape-configs
  namespace: monitoring
stringData:
  additional-scrape-configs.yaml: |
    - job_name: 'pihole-exporter'
      scrape_interval: 15s
      metrics_path: /metrics
      static_configs:
        - targets:
            - "pihole-exporter.pihole.svc.cluster.local:9617"
```

The Prometheus configuration in `values.yaml` points to this Secret.

```yaml
prometheus:
  prometheusSpec:
    additionalScrapeConfigs:
      name: additional-scrape-configs
      key: additional-scrape-configs.yaml
```

## Grafana Configuration

Grafana uses a sidecar container for dashboards which loads them dynamically
from ConfigMaps.

The sidecar searches for ConfigMaps in the `monitoring` namespace with the label
`grafana_dashboard: "1"`.

Grafana's `values.yaml` includes settings for the sidecar.

```yaml
grafana:
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
  service:
    type: LoadBalancer
    loadBalancerIP: 192.168.1.123
  adminPassword: 'admin'
  image:
    tag: 11.3.0
```

A ConfigMap, like `grafana-dashboard-pihole`, contains the Grafana dashboard
JSON and uses the required label. This ConfigMap is generated using Kustomize's
`configMapGenerator`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-pihole
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  pihole-dashboard.json: |
    { ...JSON dashboard definition... }
```

Grafana's sidecar loads any matching ConfigMap when it's created or updated.
