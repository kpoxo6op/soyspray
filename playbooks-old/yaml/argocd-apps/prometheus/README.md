# Prometheus, AlertManager, and Telegram Integration

```text
                                                  ┌─────────────────┐
                                                  │                 │
                                                  │  Telegram Bot   │
                                                  │                 │
                                                  └────────▲────────┘
                                                           │
                                                           │
┌──────────────┐         ┌──────────────┐         ┌─────────┴───────┐
│              │         │              │         │                 │
│  Prometheus  ├────────►│ AlertManager ├────────►│ Secret:         │
│              │  Alert  │              │   Uses  │ bot_token       │
└──────┬───────┘         └──────────────┘         │                 │
       │                                          └─────────────────┘
       │
       │ Evaluates
       ▼
┌──────────────┐
│ PrometheusRules:
│ - temperature│
│ - other      │
└──────────────┘
```

## Monitoring Status

### Currently Monitored Applications

| Application | Status | Endpoint | Method |
|-------------|--------|----------|--------|
| **Infrastructure** |
| Kubernetes API Server | ✅ Up | `192.168.1.10:6443` | ServiceMonitor |
| CoreDNS | ✅ Up | Internal | ServiceMonitor |
| Kubelet (3 endpoints) | ✅ Up | `192.168.1.10:10250` | ServiceMonitor |
| Kube Proxy | ✅ Up | `192.168.1.10:10249` | ServiceMonitor |
| Kube Controller Manager | ✅ Up | `192.168.1.10:10257` | ServiceMonitor |
| Kube Scheduler | ✅ Up | `192.168.1.10:10259` | ServiceMonitor |
| Kube State Metrics | ✅ Up | Internal | ServiceMonitor |
| Node Exporter | ✅ Up | `192.168.1.10:9100` | ServiceMonitor |
| **Applications** |
| ArgoCD | ✅ Up | Internal | ServiceMonitor (custom) |
| cert-manager | ✅ Up | Internal | ServiceMonitor (custom) |
| **Prometheus Stack** |
| Prometheus | ✅ Up | Internal | ServiceMonitor |
| AlertManager | ✅ Up | Internal | ServiceMonitor |
| Prometheus Operator | ✅ Up | Internal | ServiceMonitor |
| Grafana | ✅ Monitored | Internal | ServiceMonitor |

### Applications with Metrics Available (Not Yet Monitored)

| Application | Namespace | Metrics Port | Notes |
|-------------|-----------|--------------|-------|
| **ingress-nginx** | ingress-nginx | `:10254` | Request rates, latencies, status codes |
| **PostgreSQL (CNPG)** | postgresql | `:9187` | DB performance, connections, queries |
| **Longhorn** | longhorn-system | Built-in | Storage metrics (volume health, IOPS, capacity) |
| **Redis** | redis | N/A | No built-in exporter, needs redis-exporter sidecar |

### How to Discover Metrics

**List all ServiceMonitors:**
```bash
kubectl get servicemonitor -A
```

**List all PodMonitors:**
```bash
kubectl get podmonitor -A
```

**Query Prometheus for active targets:**
```bash
kubectl exec -n monitoring prometheus-kube-prometheus-stack-prometheus-0 -c prometheus -- \
  wget -qO- http://localhost:9090/api/v1/targets 2>/dev/null | \
  jq -r '.data.activeTargets[] | "\(.labels.job) - \(.health) - \(.scrapeUrl)"' | \
  sort | uniq
```

**Find services with metrics ports:**
```bash
kubectl get svc -A -o json | \
  jq -r '.items[] | select(.spec.ports[]? | select(.name | test("metric|prom|monitor"; "i"))) |
  "\(.metadata.namespace)/\(.metadata.name) - Port: \(.spec.ports[] |
  select(.name | test("metric|prom|monitor"; "i")) | "\(.name):\(.port)")"' | sort
```

**Check specific pod ports:**
```bash
# Example for ingress-nginx
kubectl get pods -n ingress-nginx -o json | \
  jq -r '.items[0].spec.containers[0].ports[] | "\(.name): \(.containerPort)"'

# Example for PostgreSQL CNPG
kubectl get pods -n postgresql -o json | \
  jq -r '.items[0].spec.containers[] | "\(.name): \(.ports[]? | "\(.name):\(.containerPort)")"'
```

**List all running application pods:**
```bash
kubectl get pods -A --field-selector=status.phase=Running -o json | \
  jq -r '.items[] | select(.metadata.namespace != "kube-system" and
  .metadata.namespace != "monitoring" and .metadata.namespace != "longhorn-system") |
  "\(.metadata.namespace)/\(.metadata.name)"' | sort
```

