# Kong operator dashboard

This Kustomize package connects Kong metrics to the existing monitoring stack.

- [`kong-prometheus-plugin.yaml`](kong-prometheus-plugin.yaml) enables Kong's
  Prometheus plugin.
- [`kong-gateway-podmonitor.yaml`](kong-gateway-podmonitor.yaml) selects the
  gateway pods for scraping.
- [`kong-prometheus-scrape-networkpolicy.yaml`](kong-prometheus-scrape-networkpolicy.yaml)
  permits the monitoring path.
- [`dashboards/`](dashboards/) contains the Grafana dashboard definition.
- [`kustomization.yaml`](kustomization.yaml) assembles the package and generates
  the dashboard ConfigMap.
