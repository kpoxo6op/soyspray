# Prometheus and Grafana Setup

Custom Scrape Jobs defined in Kubernetes Secrets and referenced in Prometheus
  values.

`values.yaml`

```yaml
prometheus:
  prometheusSpec:
    replicas: 1
    retention: 15d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: local-storage
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
    additionalScrapeConfigs:
      name: additional-scrape-configs
      key: additional-scrape-configs.yaml
```

How It Works

Prometheus scrape jobs are stored in a Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
    name: additional-scrape-configs
    namespace: monitoring
    labels:
    app.kubernetes.io/managed-by: argo-cd
stringData:
    additional-scrape-configs.yaml: |
    - job_name: 'pihole-exporter'
        scrape_interval: 15s
        metrics_path: /metrics
        static_configs:
        - targets:
            - "pihole-exporter.pihole.svc.cluster.local:9617"
```

Prometheus Links the Secret referenced in `values.yaml` under
   `additionalScrapeConfigs`.

## Grafana Configuration

Sidecar for Dashboards loads dashboards dynamically from ConfigMaps based on a
label.

`values.yaml`

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
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
```

The sidecar watches for ConfigMaps in the `monitoring` namespace labeled with
   `grafana_dashboard: "1"`.

ConfigMap Example

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

Any matching ConfigMap created or updated is loaded automatically by the
   sidecar.

```text

Prometheus                             Grafana

+--values.yaml-------+                  +--------------------+
| Prometheus Config  |                  | Grafana Config     |
| - Retention: 15d   |                  | - Sidecar enabled  |
| - Storage: Local   |                  | - Label: dashboard |
| - Scrape configs   |                  | - LoadBalancer IP  |
+--------------------+                  +--------------------+
          |                                        |
          v                                        v
+additional-scrape-configs-+            +--------------------+
| Kubernetes Secret  |                  | grafana-dashboard-pihole ConfigMap |
| - Stores scrape    |                  | - Dashboard JSON   |
|   job configs      |                  | - Label: dashboard |
| - Target: pihole   |                  +--------------------+
+--------------------+                            |
          |                                        |
          v                                        v
+--values.yaml-------+                  +--------------------+
| Prometheus         | <-- Connects --> | Grafana           |
| - Collects metrics |                  | - Visualizes data |
| - Exposes data     |                  | - Sidecar loads   |
+--------------------+                  |   dashboards      |
                                        +--------------------+
```
