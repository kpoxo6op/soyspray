# How to Check Rendered Charts

```sh
helm template prometheus-stack prometheus-community/kube-prometheus-stack -f apps/prometheus/values.yaml > rendered.yaml
```
