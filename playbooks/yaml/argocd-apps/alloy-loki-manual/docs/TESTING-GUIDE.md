# Loki Stack Testing Guide

**Purpose**: Step-by-step manual testing procedures to verify the Loki log aggregation and alerting stack is working correctly.

## Quick Health Check

## Test 1: Verify Loki Server Health

### Check Loki is Ready

```bash
# Port-forward to Loki (run in background)
kubectl port-forward -n monitoring svc/loki 3100:3100 &

# Wait for port-forward to establish
sleep 2

# Check ready endpoint
curl -s http://localhost:3100/ready
```

**Expected Output:**
```
ready
```

### Check Loki Version and Config

```bash
# Check build info
curl -s http://localhost:3100/loki/api/v1/status/buildinfo | jq
```

**Expected Output:**
```json
{
  "status": "success",
  "data": {
    "version": "3.3.2",
    "revision": "...",
    "branch": "HEAD",
    "buildUser": "...",
    "buildDate": "...",
    "goVersion": "..."
  }
}
```

**✅ Pass Criteria**: Returns `"version": "3.3.2"` and status is success.

---

## Test 2: Verify Log Ingestion

### Check Available Job Labels

```bash
curl -s 'http://localhost:3100/loki/api/v1/label/job/values' | jq
```

**Expected Output:**
```json
{
  "status": "success",
  "data": [
    "kubernetes-events",
    "kubernetes-pods"
  ]
}
```

**✅ Pass Criteria**: Both `kubernetes-events` and `kubernetes-pods` jobs are present.

### Check Namespace Labels

```bash
curl -s 'http://localhost:3100/loki/api/v1/label/namespace/values' | jq
```

**Expected Output:**
```json
{
  "status": "success",
  "data": [
    "argocd",
    "cert-manager",
    "kube-system",
    "monitoring",
    "..."
  ]
}
```

**✅ Pass Criteria**: Multiple namespaces are listed (shows logs from different namespaces).

### Query Recent Kubernetes Events

```bash
# Query events from last hour
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="kubernetes-events"}' \
  --data-urlencode 'limit=10' \
  --data-urlencode 'start='$(date -u -d '1 hour ago' +%s) | jq '.data.result | length'
```

**Expected Output:**
```
5  (or any number > 0)
```

**✅ Pass Criteria**: Returns count greater than 0, indicating events are flowing.

### Query Recent Pod Logs

```bash
# Query pod logs from last hour
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="kubernetes-pods"}' \
  --data-urlencode 'limit=10' \
  --data-urlencode 'start='$(date -u -d '1 hour ago' +%s) | jq '.data.result | length'
```

**Expected Output:**
```
10  (or any number > 0)
```

**✅ Pass Criteria**: Returns count greater than 0, indicating pod logs are flowing.

---

## Test 3: Verify Alert Rules Loaded

### Check Loki Ruler Status

```bash
curl -s 'http://localhost:3100/loki/api/v1/rules' | head -100
```

**Expected Output:**
```yaml
application-errors.yaml:
    - name: application-errors
      rules:
        - alert: ApplicationErrorBurst
          expr: |
            sum by (namespace, pod) (
              count_over_time({cluster="soyspray", job="kubernetes-pods"} |~ "(?i)\\b(error|fatal)\\b" [5m])
            ) > 50
          for: 5m
          labels:
            severity: warning

kubernetes-critical.yaml:
    - name: kubernetes-critical
      rules:
        - alert: KubernetesPodCrashLoopingLogs
          ...

storage-mount-failures.yaml:
    - name: storage-mount-failures
      rules:
        - alert: VolumeMountAttachFailures
          ...
```

**✅ Pass Criteria**: All three rule groups are listed without errors.

### Verify No Ruler Errors in Logs

```bash
kubectl logs -n monitoring loki-0 --tail=50 | grep -i "ruler" | grep -i "error"
```

**Expected Output:**
```
(empty - no errors)
```

**✅ Pass Criteria**: No ruler-related errors in recent logs.

---

## Test 4: Test Alert Rule Firing

### Test ApplicationErrorBurst Alert

**Create a pod that generates error logs:**

```bash
# Create test pod that logs errors rapidly
kubectl run error-test-$(date +%s) \
  --image=busybox \
  --restart=Never \
  --namespace=default \
  --labels="test=loki-alert" \
  -- sh -c '
    for i in $(seq 1 100); do
      echo "ERROR: Test error message number $i"
      sleep 1
    done
  '
```

**Wait and check if logs are ingested:**

```bash
# Wait 30 seconds for logs to be ingested
sleep 30

# Query for error logs from test pod
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={namespace="default"} |= "error-test" |= "ERROR"' \
  --data-urlencode 'limit=5' \
  --data-urlencode 'start='$(date -u -d '5 minutes ago' +%s) \
  | jq '.data.result[0].values[:5]'
```

**Expected Output:**
```json
[
  [
    "1729054321000000000",
    "ERROR: Test error message number 1"
  ],
  [
    "1729054322000000000",
    "ERROR: Test error message number 2"
  ],
  ...
]
```

**Check Alert Manager for Pending Alert:**

Wait 5 minutes (for: 5m in the rule), then check Alertmanager:

```bash
# Port-forward to Alertmanager
kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093 &
sleep 2

# Check for alerts
curl -s 'http://localhost:9093/api/v2/alerts' | jq '.[] | select(.labels.alertname=="ApplicationErrorBurst")'
```

**Expected Output:**
```json
{
  "labels": {
    "alertname": "ApplicationErrorBurst",
    "namespace": "default",
    "pod": "error-test-xxxxx",
    "severity": "warning"
  },
  "status": {
    "state": "active"
  },
  ...
}
```

**Clean up test pod:**

```bash
kubectl delete pod -n default -l test=loki-alert
```

**✅ Pass Criteria**: Alert appears in Alertmanager after 5 minutes, then resolves after cleanup.

---

## Test 5: Test Kubernetes Events Alert

### Test KubernetesPodCrashLoopingLogs Alert

**Create a pod that crashes:**

```bash
# Create pod that exits immediately (will crash loop)
kubectl run crash-test-$(date +%s) \
  --image=busybox \
  --namespace=default \
  --labels="test=loki-alert" \
  -- sh -c 'exit 1'
```

**Query for CrashLoopBackOff events:**

```bash
# Wait 2 minutes for events to accumulate
sleep 120

# Query for crash loop events
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="kubernetes-events"} |= "Back-off restarting failed container"' \
  --data-urlencode 'limit=5' \
  --data-urlencode 'start='$(date -u -d '10 minutes ago' +%s) \
  | jq '.data.result[0].values[:3]'
```

**Expected Output:**
```json
[
  [
    "1729054400000000000",
    "... Back-off restarting failed container ..."
  ],
  ...
]
```

**Check for alert after 10 minutes:**

```bash
# Wait for alert to fire (for: 10m in rule)
# Then check Alertmanager
curl -s 'http://localhost:9093/api/v2/alerts' \
  | jq '.[] | select(.labels.alertname=="KubernetesPodCrashLoopingLogs")'
```

**Clean up:**

```bash
kubectl delete pod -n default -l test=loki-alert
```

**✅ Pass Criteria**: CrashLoopBackOff events are logged and alert fires after 10 minutes.

---

## Test 6: Verify Prometheus Integration

### Check ServiceMonitor for Loki

```bash
kubectl get servicemonitor -n monitoring loki -o yaml | grep -A 10 "spec:"
```

**Expected Output:**
```yaml
spec:
  endpoints:
  - interval: 30s
    path: /metrics
    port: http
  namespaceSelector:
    matchNames:
    - monitoring
  selector:
    matchLabels:
      app.kubernetes.io/name: loki
```

### Check PodMonitor for Alloy

```bash
kubectl get podmonitor -n monitoring alloy -o yaml | grep -A 10 "spec:"
```

**Expected Output:**
```yaml
spec:
  podMetricsEndpoints:
  - interval: 30s
    path: /metrics
    port: http-metrics
  selector:
    matchLabels:
      app.kubernetes.io/name: grafana-alloy
```

### Verify Prometheus Can Scrape Loki

If you have access to Prometheus UI:

```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090 &
```

Then visit: `http://localhost:9090/targets`

Look for:
- Target: `monitoring/loki/0` - State should be **UP**
- Target: `monitoring/alloy-*` - State should be **UP**

**✅ Pass Criteria**: All targets show UP status.

---

## Test 7: End-to-End Alert to Telegram

### Prerequisites

- Telegram bot configured
- Secret `alertmanager-telegram-secret` exists
- Alertmanager configured with Telegram receiver

### Verify Telegram Configuration

```bash
# Check secret exists
kubectl get secret -n monitoring alertmanager-telegram-secret

# Check Alertmanager config has telegram receiver
kubectl get secret -n monitoring \
  alertmanager-kube-prometheus-stack-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' \
  | base64 -d | grep -A 5 "telegram"
```

**Expected Output:**
```yaml
receivers:
- name: telegram
  telegram_configs:
  - api_url: https://api.telegram.org
    bot_token_file: /etc/alertmanager/telegram/PROMETHEUS_TELEGRAM_BOT_TOKEN
    chat_id: 336642153
```

### Trigger Test Alert and Verify Telegram Delivery

**Option A: Use existing error-test pod**

Follow Test 4 above to create error-test pod, then:

1. Wait 5 minutes for alert to fire
2. Check your Telegram (chat ID: 336642153)
3. You should receive message like:

```
🔴 [FIRING:1] ApplicationErrorBurst

Error burst in default/error-test-xxxxx

More than 50 log lines containing 'error' or 'fatal' were observed in 5m for pod default/error-test-xxxxx. Investigate recent deployments, crashes, or upstream dependencies.

Labels:
  alertname: ApplicationErrorBurst
  namespace: default
  pod: error-test-xxxxx
  severity: warning
```

**Option B: Send test alert directly to Alertmanager**

```bash
# Send test alert to Alertmanager
curl -H 'Content-Type: application/json' -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning",
    "namespace": "default",
    "pod": "test-pod"
  },
  "annotations": {
    "summary": "Test alert from manual testing",
    "description": "This is a test alert to verify Telegram integration"
  },
  "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'"
}]' http://localhost:9093/api/v2/alerts
```

Check Telegram within 30-60 seconds for test alert.

**✅ Pass Criteria**: Alert message arrives in Telegram chat.

---

## Test 8: Verify RBAC Permissions

### Check Alloy Can Read Pod Logs

```bash
# Check Alloy ServiceAccount
kubectl get sa -n monitoring alloy

# Check ClusterRole permissions
kubectl describe clusterrole alloy | grep -A 20 "Resources"
```

**Expected Output:**
```
Resources  Non-Resource URLs  Resource Names  Verbs
---------  -----------------  --------------  -----
pods       []                 []              [get list watch]
pods/log   []                 []              [get]
...
```

### Check Alloy Logs for Permission Errors

```bash
kubectl logs -n monitoring daemonset/alloy --tail=50 | grep -i "forbidden" | head -5
```

**Expected Output:**
```
(warnings about specific namespaces may appear - this is normal if not all namespaces are accessible)
```

**✅ Pass Criteria**: Alloy has `pods` and `pods/log` permissions. Some "forbidden" warnings are acceptable if intentionally limiting access.

---

## Test 9: Query LogQL Directly

### Test Label Matchers

```bash
# Query logs by namespace
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={namespace="monitoring"}' \
  --data-urlencode 'limit=5' \
  --data-urlencode 'start='$(date -u -d '1 hour ago' +%s) \
  | jq '.data.result | length'

# Query logs by job
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="kubernetes-pods", namespace="monitoring"}' \
  --data-urlencode 'limit=5' \
  --data-urlencode 'start='$(date -u -d '1 hour ago' +%s) \
  | jq '.data.result | length'
```

### Test Log Filters

```bash
# Find logs containing "error" (case-insensitive)
curl -G -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="kubernetes-pods"} |~ "(?i)error"' \
  --data-urlencode 'limit=10' \
  --data-urlencode 'start='$(date -u -d '1 hour ago' +%s) \
  | jq '.data.result[0].values[:3]'
```

### Test Metric Queries

```bash
# Count log lines per namespace in last hour
curl -G -s 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query=sum by (namespace) (count_over_time({job="kubernetes-pods"}[1h]))' \
  | jq '.data.result'
```

**✅ Pass Criteria**: All queries return results without errors.

---

## Test 10: Verify Storage and Retention

### Check Loki Storage PVC

```bash
# Check PVC status
kubectl get pvc -n monitoring storage-loki-0

# Check PVC size
kubectl get pvc -n monitoring storage-loki-0 -o jsonpath='{.spec.resources.requests.storage}'
```

**Expected Output:**
```
NAME              STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
storage-loki-0    Bound    pvc-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   10Gi       RWO            longhorn       Xh

10Gi
```

### Check Loki Storage Usage

```bash
# Get storage usage from Loki pod
kubectl exec -n monitoring loki-0 -- df -h /var/loki
```

**Expected Output:**
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/xxx        10G   1.2G  8.8G  12% /var/loki
```

### Verify Retention Settings

```bash
# Check retention in Loki config
kubectl get cm -n monitoring loki-config -o yaml | grep -A 5 "retention"
```

**Expected Output:**
```yaml
retention_period: 14d
retention_enabled: true
```

**✅ Pass Criteria**:
- PVC is Bound with 10Gi capacity
- Storage is not full (< 80% used)
- Retention configured for 14 days

---

## Troubleshooting Common Issues

### Issue: No Logs Ingested

**Check:**
1. Are Alloy pods running?
   ```bash
   kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana-alloy
   ```

2. Check Alloy logs for errors:
   ```bash
   kubectl logs -n monitoring daemonset/alloy --tail=100
   ```

3. Verify Loki is reachable from Alloy:
   ```bash
   kubectl exec -n monitoring -it <alloy-pod> -- \
     wget -O- http://loki.monitoring.svc.cluster.local:3100/ready
   ```

### Issue: Alerts Not Firing

**Check:**
1. Are rules loaded?
   ```bash
   curl -s http://localhost:3100/loki/api/v1/rules
   ```

2. Check Loki ruler logs:
   ```bash
   kubectl logs -n monitoring loki-0 | grep ruler
   ```

3. Verify Alertmanager connection:
   ```bash
   kubectl exec -n monitoring loki-0 -- \
     wget -O- http://alertmanager-operated.monitoring.svc:9093/-/healthy
   ```

### Issue: Telegram Notifications Not Received

**Check:**
1. Is Telegram secret configured?
   ```bash
   kubectl get secret -n monitoring alertmanager-telegram-secret
   ```

2. Check Alertmanager logs:
   ```bash
   kubectl logs -n monitoring alertmanager-kube-prometheus-stack-alertmanager-0
   ```

3. Verify bot token is valid (check Telegram BotFather)

---

## Cleanup After Testing

```bash
# Stop all port-forwards
pkill -f 'port-forward.*loki'
pkill -f 'port-forward.*alertmanager'
pkill -f 'port-forward.*prometheus'

# Delete test pods
kubectl delete pod -n default -l test=loki-alert

# Delete any remaining error-test or crash-test pods
kubectl get pods --all-namespaces | grep -E "error-test|crash-test" | \
  awk '{print $1, $2}' | xargs -n2 kubectl delete pod -n
```

---

## Success Criteria Summary

Your Loki stack is fully operational if:

- ✅ All pods (loki-0, alloy-*, alloy-events-*) are Running and Ready
- ✅ Loki `/ready` endpoint returns "ready"
- ✅ Both `kubernetes-pods` and `kubernetes-events` jobs appear in label query
- ✅ All 3 alert rules loaded without errors
- ✅ Test error logs trigger ApplicationErrorBurst alert
- ✅ Test crash loop triggers KubernetesPodCrashLoopingLogs alert
- ✅ Prometheus ServiceMonitor and PodMonitor targets are UP
- ✅ Telegram notifications are received when alerts fire
- ✅ PVC storage is healthy and within limits

---

## Additional Resources

- **Alert Pipeline Diagram**: See `ALERT-PIPELINE.md`
- **Deployment Status**: See `DEPLOYMENT-STATUS-*.md`
- **Loki Documentation**: https://grafana.com/docs/loki/latest/
- **Alloy Documentation**: https://grafana.com/docs/alloy/latest/
- **LogQL Reference**: https://grafana.com/docs/loki/latest/query/

---

## Quick Reference Commands

```bash
# View all Loki stack pods
kubectl get pods -n monitoring -l 'app.kubernetes.io/name in (loki,grafana-alloy)'

# Port-forward to Loki
kubectl port-forward -n monitoring svc/loki 3100:3100

# Check Loki health
curl http://localhost:3100/ready

# Query job labels
curl -s 'http://localhost:3100/loki/api/v1/label/job/values' | jq

# Check alert rules
curl -s 'http://localhost:3100/loki/api/v1/rules' | head -50

# View Loki logs
kubectl logs -n monitoring loki-0 --tail=50

# View Alloy logs
kubectl logs -n monitoring daemonset/alloy --tail=50

# Port-forward to Alertmanager
kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093

# Check active alerts
curl -s 'http://localhost:9093/api/v2/alerts' | jq

# Sync Loki ArgoCD app
argocd app sync loki
```

---

**Last Verified**: 2025-10-16
**Status**: ✅ All tests passing with commit `f5020ce`

