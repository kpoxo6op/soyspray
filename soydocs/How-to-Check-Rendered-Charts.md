# How to Check Rendered Charts

```sh
helm template prometheus-stack prometheus-community/kube-prometheus-stack -f playbooks/yaml/argocd-apps/prometheus/values.yaml > rendered.yaml
```
