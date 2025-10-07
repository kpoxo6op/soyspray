# How to Check Rendered Charts

```sh
helm template prometheus-stack prometheus-community/kube-prometheus-stack -f playbooks/argocd/apps/prometheus/values.yaml > rendered.yaml
```
