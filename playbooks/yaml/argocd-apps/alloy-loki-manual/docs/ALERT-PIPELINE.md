# Loki Alert Pipeline: From Logs to Telegram

## Complete Flow Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: LOG COLLECTION                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐          ┌──────────────────────┐
│ Alloy DaemonSet      │          │ Alloy Events         │
│ (on every node)      │          │ (single deployment)  │
│                      │          │                      │
│ Collects:            │          │ Collects:            │
│ /var/log/pods/*/*.log│          │ K8s Events API       │
│                      │          │                      │
│ Labels added:        │          │ Labels added:        │
│ - job=kubernetes-pods│          │ - job=kubernetes-events
│ - namespace          │          │ - namespace          │
│ - pod                │          │ - reason             │
│ - container          │          │ - type (Warning/Normal)
│ - cluster=soyspray   │          │ - involved_object_*  │
└─────────┬────────────┘          └──────────┬───────────┘
          │                                  │
          │ HTTP Push                        │ HTTP Push
          │ :3100/loki/api/v1/push          │ :3100/loki/api/v1/push
          │                                  │
          └──────────────┬───────────────────┘
                         │
                         ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: LOG STORAGE & INDEXING                                              │
└─────────────────────────────────────────────────────────────────────────────┘

          ┌──────────────────────────┐
          │ Loki StatefulSet         │
          │ (monitoring namespace)   │
          │                          │
          │ Components:              │
          │ 1. Ingester             │◄── Receives logs from Alloy
          │ 2. Querier              │◄── Queried by Ruler
          │ 3. Ruler ⚡             │◄── Evaluates alert rules
          │ 4. Compactor            │
          │                          │
          │ Storage:                 │
          │ /var/loki/chunks/       │
          │ /var/loki/index/        │
          │ (50Gi Longhorn PVC)     │
          └─────────┬────────────────┘
                    │
                    │ Mounts ConfigMaps:
                    │ - /etc/loki/config.yaml (loki-config)
                    │ - /etc/loki/rules/*.yaml (projected volume) ◄── YOUR RULES HERE!
                    │   ├── loki-rules-kubernetes
                    │   └── loki-rules-backup
                    │
                    ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: RULE EVALUATION (Loki Ruler Component)                              │
└─────────────────────────────────────────────────────────────────────────────┘

          ┌─────────────────────────────────────┐
          │ Projected Volume: Rules ConfigMaps   │
          │ (/etc/loki/rules/)                  │
          │                                     │
          │ ┌─────────────────────────────────┐ │
          │ │ loki-rules-kubernetes ConfigMap│ │
          │ │                                 │ │
          │ │ • kubernetes-critical.yaml     │ │
          │ │   - KubernetesPodCrashLoopingLogs│ │
          │ │                                 │ │
          │ │ • application-errors.yaml      │ │
          │ │   - ApplicationErrorBurst       │ │
          │ │     count_over_time(...|~ "error")│ │
          │ │                                 │ │
          │ │ • storage-mount-failures.yaml  │ │
          │ │   - VolumeMountAttachFailures   │ │
          │ │     |~ "FailedMount|Failed..." │ │
          │ └─────────────────────────────────┘ │
          │                                     │
          │ ┌─────────────────────────────────┐ │
          │ │ loki-rules-backup ConfigMap    │ │
          │ │                                 │ │
          │ │ • immich-backup.yaml           │ │
          │ │ • immich-backup-events.yaml    │ │
          │ │ • cnpg-backup.yaml             │ │
          │ │ • backup-error-burst.yaml       │ │
          │ └─────────────────────────────────┘ │
          └─────────────────────────────────────┘
                           │
                           │ Ruler runs LogQL queries every 1m
                           │ Example: count_over_time({job="kubernetes-pods"}
                           │          |~ "error"[5m]) > 50
                           ▼
          ┌──────────────────────────────────────┐
          │ Loki Ruler evaluates:                │
          │                                      │
          │ FOR ApplicationErrorBurst:           │
          │ 1. Query logs: job=kubernetes-pods   │
          │ 2. Filter: |~ "(?i)\b(error|fatal)\b"│
          │ 3. Count over 5m window              │
          │ 4. Group by (namespace, pod)         │
          │ 5. Threshold: > 50 lines             │
          │ 6. Wait: 5m (for: 5m)                │
          │ 7. IF TRUE → Fire Alert              │
          └──────────────┬───────────────────────┘
                         │
                         │ Alert Payload:
                         │ {
                         │   "alertname": "ApplicationErrorBurst",
                         │   "namespace": "media",
                         │   "pod": "radarr-7d8f9c-xyz",
                         │   "severity": "warning",
                         │   "summary": "Error burst in media/radarr-7d8f9c-xyz"
                         │ }
                         │
                         ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: ALERT ROUTING (Alertmanager)                                        │
└─────────────────────────────────────────────────────────────────────────────┘

          ┌───────────────────────────────────────┐
          │ Alertmanager                          │
          │ (deployed by kube-prometheus-stack)   │
          │                                       │
          │ Configuration:                        │
          │ - LoadBalancer: 192.168.50.206        │
          │ - Config: prometheus/values.yaml      │
          │                                       │
          │ ┌───────────────────────────────────┐ │
          │ │ Route Configuration:              │ │
          │ │                                   │ │
          │ │ route:                            │ │
          │ │   group_by: ["alertname"]         │ │
          │ │   group_wait: 30s                 │ │
          │ │   group_interval: 5m              │ │
          │ │   repeat_interval: 4h             │ │
          │ │   receiver: "telegram"            │ │
          │ │   routes:                         │ │
          │ │     - matchers:                   │ │
          │ │       - severity=~"warning|critical"│ │
          │ │       receiver: "telegram"        │ │
          │ └───────────────────────────────────┘ │
          │                                       │
          │ Processing:                           │
          │ 1. Receive alert from Loki Ruler      │
          │ 2. Check severity (warning/critical)  │
          │ 3. Group by alertname                 │
          │ 4. Wait 30s for more alerts           │
          │ 5. Send to telegram receiver          │
          └──────────────┬────────────────────────┘
                         │
                         ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: TELEGRAM NOTIFICATION                                               │
└─────────────────────────────────────────────────────────────────────────────┘

          ┌──────────────────────────────────────┐
          │ Telegram Receiver Configuration:     │
          │                                      │
          │ receivers:                           │
          │   - name: "telegram"                 │
          │     telegram_configs:                │
          │       - api_url: "https://api.telegram.org"
          │         bot_token_file: /etc/alertmanager/telegram/
          │                         PROMETHEUS_TELEGRAM_BOT_TOKEN
          │         chat_id: 336642153           │
          └──────────────┬───────────────────────┘
                         │
                         │ Secret mounted from:
                         │ alertmanager-telegram-secret
                         │ (contains bot token)
                         │
                         ▼
          ┌──────────────────────────────────────┐
          │ Telegram API                         │
          │ https://api.telegram.org             │
          └──────────────┬───────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────────────┐
          │  📱 Your Telegram                    │
          │                                      │
          │  🔴 [FIRING:1] ApplicationErrorBurst │
          │                                      │
          │  Error burst in media/radarr-xyz     │
          │                                      │
          │  More than 50 log lines containing   │
          │  'error' or 'fatal' were observed    │
          │  in 5m for pod media/radarr-xyz.     │
          │  Investigate recent deployments...   │
          │                                      │
          │  Labels:                             │
          │    alertname: ApplicationErrorBurst  │
          │    namespace: media                  │
          │    pod: radarr-7d8f9c-xyz           │
          │    severity: warning                 │
          └──────────────────────────────────────┘
```

## Configuration File Locations

### 1. Log Collection Configuration
**Location**: `playbooks/yaml/argocd-apps/alloy-loki-manual/`
- `alloy-configmap.yaml` - Pod logs collection
- `alloy-events-configmap.yaml` - Kubernetes events collection
- `alloy-daemonset.yaml` - DaemonSet running on every node
- `alloy-events-deployment.yaml` - Events collector deployment

### 2. Loki Storage & Rules
**Location**: `playbooks/yaml/argocd-apps/alloy-loki-manual/`
- `loki-configmap.yaml` - Loki server configuration
  - Line 64-73: Ruler configuration pointing to Alertmanager
- `loki-rules-kubernetes.yaml` - **Platform & Kubernetes Rules** ⚡
  - `kubernetes-critical.yaml` - KubernetesPodCrashLoopingLogs
  - `application-errors.yaml` - ApplicationErrorBurst
  - `storage-mount-failures.yaml` - VolumeMountAttachFailures
- `loki-rules-backup.yaml` - **Backup & Database Rules** ⚡
  - `immich-backup.yaml` - ImmichMediaBackupFailureImmediate
  - `immich-backup-events.yaml` - ImmichMediaBackupBackoffLimitExceeded
  - `cnpg-backup.yaml` - CNPGBackupBarmanError, CNPGWalArchiveFailure
  - `backup-error-burst.yaml` - BackupErrorBurst
- `loki-statefulset.yaml` - Uses projected volume to mount both rule ConfigMaps

### 3. Alertmanager Configuration
**Location**: `playbooks/yaml/argocd-apps/prometheus/`
- `values.yaml` - Lines 145-184
  - Telegram bot token mount
  - Route configuration
  - Receiver configuration

## How Rules Work

### Example: ApplicationErrorBurst

```yaml
- alert: ApplicationErrorBurst
  expr: |
    sum by (namespace, pod) (
      count_over_time({cluster="soyspray", job="kubernetes-pods"} |~ "(?i)\b(error|fatal)\b" [5m])
    ) > 50
  for: 5m
```

**Step-by-step execution:**

1. **LogQL Query**: `{cluster="soyspray", job="kubernetes-pods"}`
   - Selects all pod logs from your cluster

2. **Log Filter**: `|~ "(?i)\b(error|fatal)\b"`
   - Case-insensitive regex match for "error" or "fatal" words

3. **Count**: `count_over_time(...[5m])`
   - Counts matching log lines in 5-minute window

4. **Group**: `sum by (namespace, pod)`
   - Groups results per namespace+pod combination

5. **Threshold**: `> 50`
   - Fires if more than 50 error lines found

6. **Pending**: `for: 5m`
   - Alert must be true for 5 minutes before firing

7. **Labels**: `severity: warning`
   - Sets alert severity for routing

## Label Flow

Labels are consistently applied through the pipeline:

```
Alloy Collection → Loki Storage → Rule Evaluation → Alert
  cluster=soyspray   cluster=soyspray   namespace=media    namespace=media
  job=kubernetes-pods job=kubernetes-pods pod=radarr-xyz   pod=radarr-xyz
  namespace=media     namespace=media                      severity=warning
  pod=radarr-xyz      pod=radarr-xyz                       alertname=...
```

## Why This Works

### Log-Based vs Metric-Based Alerts

**Metrics** (Prometheus):
- ✅ CPU, memory, disk usage
- ✅ Request rates, latencies
- ✅ Counters, gauges, histograms
- ❌ Cannot detect "error" in logs
- ❌ Cannot parse event messages

**Logs** (Loki):
- ✅ Error message patterns
- ✅ Kubernetes event messages
- ✅ Application-specific failures
- ✅ Text pattern matching
- ❌ Not suitable for numeric metrics

**Your setup has BOTH!**
- Prometheus monitors metrics
- Loki monitors logs
- Both send alerts to same Alertmanager
- Both route to same Telegram bot

## Integration Points

### 1. Loki → Alertmanager
```yaml
# loki-configmap.yaml
ruler:
  alertmanager_url: http://alertmanager-operated.monitoring.svc:9093
```

### 2. Prometheus → Loki (Metrics)
```yaml
# loki-servicemonitor.yaml
# Prometheus scrapes Loki's /metrics endpoint
# (monitors Loki's own health, not for alerts)
```

### 3. Alloy → Loki (Logs)
```yaml
# alloy-configmap.yaml
loki.write "default" {
  endpoint {
    url = "http://loki.monitoring.svc.cluster.local:3100/loki/api/v1/push"
  }
}
```

### 4. Alertmanager → Telegram
```yaml
# prometheus/values.yaml
telegram_configs:
  - api_url: "https://api.telegram.org"
    bot_token_file: /etc/alertmanager/telegram/PROMETHEUS_TELEGRAM_BOT_TOKEN
    chat_id: 336642153
```

## Testing the Pipeline

### 1. Generate Test Logs
```bash
# Create a pod that logs errors
kubectl run error-test --image=busybox --restart=Never -- sh -c '
  for i in $(seq 1 100); do
    echo "ERROR: Test error message $i"
    sleep 1
  done
'
```

### 2. Check Loki Ingestion
```bash
# Port-forward to Loki
kubectl port-forward -n monitoring svc/loki 3100:3100

# Query logs via LogQL
curl 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query={pod="error-test"} |= "ERROR"'
```

### 3. Check Ruler Evaluation
```bash
# Check Loki ruler API
curl http://localhost:3100/loki/api/v1/rules

# Should show your rules and their state
```

### 4. Check Alertmanager
```bash
# Port-forward to Alertmanager
kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093

# View active alerts
curl http://localhost:9093/api/v2/alerts
```

### 5. Check Telegram
- Wait 5 minutes (for: 5m)
- Alert should fire to Telegram chat 336642153

## Troubleshooting

### Alert Not Firing?

1. **Check Loki has logs**:
   ```bash
   kubectl logs -n monitoring loki-0 | grep "ingester"
   ```

2. **Check Ruler is running**:
   ```bash
   kubectl logs -n monitoring loki-0 | grep "ruler"
   ```

3. **Check rules are loaded**:
   ```bash
   kubectl exec -n monitoring loki-0 -- ls -la /etc/loki/rules/
   ```

4. **Check Alertmanager connectivity**:
   ```bash
   kubectl exec -n monitoring loki-0 -- wget -O- \
     http://alertmanager-operated.monitoring.svc:9093/-/healthy
   ```

### Alert Fires But No Telegram?

1. **Check Alertmanager config**:
   ```bash
   kubectl get secret -n monitoring alertmanager-kube-prometheus-stack-alertmanager \
     -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d
   ```

2. **Check Telegram secret**:
   ```bash
   kubectl get secret -n monitoring alertmanager-telegram-secret
   ```

3. **Check Alertmanager logs**:
   ```bash
   kubectl logs -n monitoring alertmanager-kube-prometheus-stack-alertmanager-0
   ```

## Summary

**Your complete observability stack:**

```
Logs (Alloy) ──┐
               ├──► Loki ──► Ruler ──┐
Events (Alloy)─┘                     │
                                     ├──► Alertmanager ──► Telegram 📱
Metrics ───────────► Prometheus ─────┘
```

- **2 log pipelines**: Pod logs + K8s events
- **1 metrics pipeline**: Prometheus scraping
- **3 alert rules**: Errors, crashes, storage failures
- **1 notification channel**: Telegram
- **100% GitOps**: All config in this repo

