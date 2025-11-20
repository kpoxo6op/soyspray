# Backup Monitoring Setup

This branch adds comprehensive backup monitoring for Immich media and database backups using Prometheus alerts, with zero S3 API costs.

## Overview

The monitoring system tracks two critical backup processes:
1. **Media Backup**: Immich media files synced to S3 via CronJob
2. **Database Backup**: PostgreSQL database backed up via CloudNativePG (CNPG)

Both systems are monitored using Prometheus metrics and alert when backups become stale (>36 hours old).

## Architecture

```
┌─────────────────────┐
│  Immich CronJob     │──┐
│  (media backup)     │  │
└─────────────────────┘  │
                         ├──> kube-state-metrics ──┐
┌─────────────────────┐  │                         │
│  CNPG Cluster       │──┘                         │
│  (DB backup)        │                            ├──> Prometheus ──> Alertmanager ──> Telegram
│  Port 9187          │────> CNPG Exporter ────────┘
└─────────────────────┘
```

## Components Created/Modified

### 1. CNPG PodMonitor Configuration

**File**: `playbooks/yaml/argocd-apps/cnpg/immich-db/immich-db-cluster.yaml`

Added monitoring configuration to the immich-db cluster:

```yaml
spec:
  monitoring:
    enablePodMonitor: true
```

**What this does**:
- Enables CNPG's built-in Prometheus exporter on port 9187
- Creates a PodMonitor resource automatically
- Exposes metrics including `cnpg_collector_last_available_backup_timestamp`

**Verify PodMonitor exists**:
```bash
kubectl get podmonitor immich-db -n postgresql
kubectl get podmonitor immich-db -n postgresql -o yaml
```

### 2. Prometheus Configuration

**File**: `playbooks/yaml/argocd-apps/prometheus/values.yaml`

Modified Prometheus to discover PodMonitors without the `release` label:

```yaml
prometheusSpec:
  # Allow discovery of PodMonitors without release label (e.g., CNPG-managed)
  podMonitorSelectorNilUsesHelmValues: false
```

**What this does**:
- By default, Prometheus only discovers PodMonitors with `release: kube-prometheus-stack` label
- CNPG creates PodMonitors without this label
- Setting this to `false` allows Prometheus to discover all PodMonitors

**Verify Prometheus is scraping CNPG**:
```bash
# Check if CNPG pod is being scraped
kubectl get podmonitor -n postgresql
kubectl get pods -n postgresql -l cnpg.io/cluster=immich-db

# Query Prometheus targets
curl -s "https://prometheus.soyspray.vip/api/v1/targets" | \
  jq '.data.activeTargets[] | select(.labels.namespace=="postgresql")'
```

### 3. Backup Alert Rules

**File**: `playbooks/yaml/argocd-apps/prometheus/alerts/backups-essential.yaml`

Created PrometheusRule with two alerts:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: backups-essential
  namespace: monitoring
  labels:
    release: kube-prometheus-stack  # REQUIRED for Prometheus to discover this rule
spec:
  groups:
    - name: backups-essential
      rules:
        - alert: ImmichMediaBackupStale
          expr: |
            time() - max by (namespace, cronjob) (
              kube_cronjob_status_last_successful_time{namespace="immich", cronjob="immich-media-offsite-sync"}
            ) > 36 * 60 * 60
          for: 15m
          labels:
            severity: warning
          annotations:
            summary: "Media backup stale (immich-media-offsite-sync)"
            description: "Last successful CronJob run is older than 36h in namespace=immich."

        - alert: CNPGBackupStale
          expr: |
            time() - max by (cluster) (
              cnpg_collector_last_available_backup_timestamp{cluster="immich-db"}
            ) > 36 * 60 * 60
          for: 15m
          labels:
            severity: critical
          annotations:
            summary: "CNPG backup stale (cluster=immich-db)"
            description: "CNPG reports last available backup older than 36h."
```

**Alert Parameters**:
- **Threshold**: 36 hours (129,600 seconds)
- **For Duration**: 15 minutes (avoid flapping)
- **Media Severity**: `warning` (less critical)
- **Database Severity**: `critical` (more critical)

#### How Staleness is Calculated

The alerts use a simple time-based calculation:

```promql
time() - <last_backup_timestamp> > threshold
```

Where:
- `time()` = Current Unix timestamp (seconds since epoch)
- `<last_backup_timestamp>` = Unix timestamp of last successful backup
- `threshold` = 36 hours = 129,600 seconds (36 × 60 × 60)

**Visual Timeline**:
```
Last Backup         Alert Pending (15min)    Alert Fires
     │                      │                      │
     ├──────────────────────┼──────────────────────┤
     0h                    36h                  36h15m

     [────── Safe ──────────][──── Stale ────────]
```

**Alert States**:
1. **`inactive`**: Backup is fresh (< 36 hours old)
2. **`pending`**: Backup is stale BUT only for < 15 minutes
3. **`firing`**: Backup has been stale for > 15 minutes → Telegram notification sent

The 15-minute `for` duration prevents **alert flapping** from temporary issues like brief job delays or pod scheduling hiccups.

**Check staleness manually**:
```bash
# Media backup age in hours
curl -sk "https://prometheus.soyspray.vip/api/v1/query?query=(time()-kube_cronjob_status_last_successful_time{namespace=\"immich\",cronjob=\"immich-media-offsite-sync\"})/3600" | \
  jq -r '.data.result[] | "Media backup age: \(.value[1]) hours"'

# Database backup age in hours
curl -sk "https://prometheus.soyspray.vip/api/v1/query?query=(time()-cnpg_collector_last_available_backup_timestamp{cluster=\"immich-db\"})/3600" | \
  jq -r '.data.result[] | "Database backup age: \(.value[1]) hours"'
```

**Verify alerts are loaded**:
```bash
# Check PrometheusRule exists
kubectl get prometheusrule backups-essential -n monitoring
kubectl get prometheusrule backups-essential -n monitoring -o yaml

# Check Prometheus has loaded the rules
curl -s "https://prometheus.soyspray.vip/api/v1/rules" | \
  jq '.data.groups[] | select(.name=="backups-essential")'
```

### 4. Kustomization Update

**File**: `playbooks/yaml/argocd-apps/prometheus/kustomization.yaml`

Added the alert file to Prometheus kustomization resources:

```yaml
resources:
  - alerts/temperature-alerts.yaml
  - alerts/backups-essential.yaml
```

**What this does**:
- Ensures the alert file is included when ArgoCD syncs Prometheus
- Kustomize bundles the alert rules with other Prometheus manifests

### 5. ArgoCD Application Updates

**Files**:
- `playbooks/yaml/argocd-apps/prometheus/prometheus-application.yaml`
- `playbooks/yaml/argocd-apps/cnpg/immich-db-application.yaml`

Updated `targetRevision` to point to the `monitoring` branch:

```yaml
spec:
  source:
    repoURL: "https://github.com/kpoxo6op/soyspray.git"
    targetRevision: "monitoring"  # Changed from "main"
    path: playbooks/yaml/argocd-apps/prometheus
```

**Important**: This ensures ArgoCD pulls from the correct branch during development.

## Metrics Reference

### CNPG Backup Metrics

CNPG exposes metrics on port 9187 of each PostgreSQL pod.

**Key Metrics**:
- `cnpg_collector_last_available_backup_timestamp` - Unix timestamp of last successful backup
- `cnpg_collector_last_failed_backup_timestamp` - Unix timestamp of last failed backup
- `cnpg_collector_first_recoverability_point` - First point in time for recovery
- `cnpg_collector_pg_wal_archive_status` - WAL archive status

**Query CNPG backup timestamp**:
```bash
# Via Prometheus API
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=cnpg_collector_last_available_backup_timestamp" | \
  jq '.data.result[] | {cluster: .metric.cluster, timestamp: .value[1], readable: (.value[1] | tonumber | strftime("%Y-%m-%d %H:%M:%S"))}'

# Expected output:
# {
#   "cluster": null,
#   "timestamp": "1760330830",
#   "readable": "2025-10-13 04:47:10"
# }
```

**Query all CNPG metrics**:
```bash
# List all CNPG metrics
curl -s "https://prometheus.soyspray.vip/api/v1/label/__name__/values" | \
  jq '.data[] | select(startswith("cnpg_"))'

# Query specific metric with labels
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=cnpg_collector_last_available_backup_timestamp{cluster=\"immich-db\"}" | jq '.'
```

### CronJob Metrics

kube-state-metrics exposes CronJob metrics automatically.

**Key Metrics**:
- `kube_cronjob_status_last_successful_time` - Unix timestamp of last successful run
- `kube_cronjob_status_last_schedule_time` - Unix timestamp of last schedule
- `kube_cronjob_next_schedule_time` - Unix timestamp of next scheduled run
- `kube_cronjob_spec_suspend` - Whether CronJob is suspended

**Query media backup timestamp**:
```bash
# Via Prometheus API
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=kube_cronjob_status_last_successful_time" | \
  jq '.data.result[] | select(.metric.namespace=="immich") | {cronjob: .metric.cronjob, timestamp: .value[1], readable: (.value[1] | tonumber | strftime("%Y-%m-%d %H:%M:%S"))}'

# Expected output:
# {
#   "cronjob": "immich-media-offsite-sync",
#   "timestamp": "1760330709",
#   "readable": "2025-10-13 04:45:09"
# }
```

**Query all CronJobs**:
```bash
# List all CronJobs with last success time
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=kube_cronjob_status_last_successful_time" | \
  jq '.data.result[] | {namespace: .metric.namespace, cronjob: .metric.cronjob, value: .value[1]}'
```

## Alert Query Examples

### Check Alert Status

```bash
# Get all alert rules
curl -s "https://prometheus.soyspray.vip/api/v1/rules" | \
  jq '.data.groups[] | select(.name=="backups-essential") | {name: .name, rules: [.rules[] | {alert: .name, state: .state, health: .health}]}'

# Expected output:
# {
#   "name": "backups-essential",
#   "rules": [
#     {
#       "alert": "ImmichMediaBackupStale",
#       "state": "inactive",
#       "health": "ok"
#     },
#     {
#       "alert": "CNPGBackupStale",
#       "state": "inactive",
#       "health": "ok"
#     }
#   ]
# }
```

### Check Active Alerts

```bash
# Get firing alerts
curl -s "https://prometheus.soyspray.vip/api/v1/alerts" | \
  jq '.data.alerts[] | select(.labels.alertname | startswith("Immich") or startswith("CNPG"))'

# When alerts are firing, this will show the active alerts
```

### Manual Alert Evaluation

```bash
# Check how long since last media backup (in hours)
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=(time()-kube_cronjob_status_last_successful_time{namespace=\"immich\",cronjob=\"immich-media-offsite-sync\"})/3600" | \
  jq '.data.result[] | {hours_since_backup: .value[1]}'

# Check how long since last DB backup (in hours)
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=(time()-cnpg_collector_last_available_backup_timestamp{cluster=\"immich-db\"})/3600" | \
  jq '.data.result[] | {hours_since_backup: .value[1]}'
```

## Deployment Workflow

### Deploy to Cluster

1. **Activate virtual environment**:
   ```bash
   source soyspray-venv/bin/activate
   ```

2. **Deploy affected applications**:
   ```bash
   # Deploy both Prometheus and immich-db
   ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
     --become --become-user=root --user ubuntu \
     playbooks/deploy-argocd-apps.yml --tags prometheus,immich-db
   ```

3. **Sync via ArgoCD** (alternative):
   ```bash
   # Login to ArgoCD
   make argo

   # Sync applications
   argocd app sync kube-prometheus-stack
   argocd app sync immich-db
   ```

### Verify Deployment

1. **Check CNPG PodMonitor**:
   ```bash
   kubectl get podmonitor immich-db -n postgresql
   ```

2. **Check Prometheus is scraping**:
   ```bash
   curl -s "https://prometheus.soyspray.vip/api/v1/targets" | \
     jq '.data.activeTargets[] | select(.labels.pod=="immich-db-1")'
   ```

3. **Check metrics are available**:
   ```bash
   # CNPG metrics
   curl -s "https://prometheus.soyspray.vip/api/v1/query?query=cnpg_collector_last_available_backup_timestamp" | jq '.data.result'

   # CronJob metrics
   curl -s "https://prometheus.soyspray.vip/api/v1/query?query=kube_cronjob_status_last_successful_time{namespace=\"immich\"}" | jq '.data.result'
   ```

4. **Check alerts are loaded**:
   ```bash
   kubectl get prometheusrule backups-essential -n monitoring

   # View in Prometheus UI
   open https://prometheus.soyspray.vip/alerts
   ```

## Troubleshooting

### CNPG Metrics Not Appearing

**Problem**: `cnpg_collector_last_available_backup_timestamp` returns no data

**Checks**:
1. Verify PodMonitor exists:
   ```bash
   kubectl get podmonitor immich-db -n postgresql
   ```

2. Check CNPG cluster has monitoring enabled:
   ```bash
   kubectl get cluster immich-db -n postgresql -o yaml | grep -A 5 monitoring:
   ```

3. Verify Prometheus can discover the PodMonitor:
   ```bash
   kubectl get prometheus -n monitoring kube-prometheus-stack-prometheus -o yaml | grep -A 5 "podMonitorSelector:"
   ```

4. Check if target is being scraped:
   ```bash
   curl -s "https://prometheus.soyspray.vip/api/v1/targets" | \
     jq '.data.activeTargets[] | select(.labels.namespace=="postgresql")'
   ```

5. Check metrics endpoint directly:
   ```bash
   kubectl port-forward -n postgresql immich-db-1 9187:9187 &
   curl http://localhost:9187/metrics | grep cnpg_collector
   ```

### Alert Rules Not Loading

**Problem**: `backups-essential` alerts don't appear in Prometheus

**Checks**:
1. Verify PrometheusRule exists:
   ```bash
   kubectl get prometheusrule backups-essential -n monitoring
   ```

2. Check for required label:
   ```bash
   kubectl get prometheusrule backups-essential -n monitoring -o yaml | grep -A 3 "labels:"
   # Should have: release: kube-prometheus-stack
   ```

3. Verify Prometheus rule selector:
   ```bash
   kubectl get prometheus -n monitoring kube-prometheus-stack-prometheus -o yaml | grep -A 5 "ruleSelector:"
   ```

4. Check Prometheus logs for errors:
   ```bash
   kubectl logs -n monitoring prometheus-kube-prometheus-stack-prometheus-0 -c prometheus | grep -i error
   ```

### CronJob Metrics Not Available

**Problem**: `kube_cronjob_status_last_successful_time` returns no data

**Checks**:
1. Verify kube-state-metrics is running:
   ```bash
   kubectl get pods -n monitoring -l app.kubernetes.io/name=kube-state-metrics
   ```

2. Check if CronJob exists:
   ```bash
   kubectl get cronjob -n immich
   ```

3. Verify kube-state-metrics is exposing CronJob metrics:
   ```bash
   kubectl port-forward -n monitoring deploy/kube-prometheus-stack-kube-state-metrics 8080:8080 &
   curl http://localhost:8080/metrics | grep kube_cronjob_status_last_successful_time
   ```

## Prometheus CLI Tools

### Using `promtool`

```bash
# Install promtool (if not already installed)
# Ubuntu/Debian
sudo apt-get install prometheus

# Check if alert rules are valid
promtool check rules playbooks/yaml/argocd-apps/prometheus/alerts/backups-essential.yaml

# Test alert expression
promtool query instant http://prometheus.soyspray.vip \
  'time() - kube_cronjob_status_last_successful_time{namespace="immich", cronjob="immich-media-offsite-sync"}'
```

### Using `curl` and `jq`

```bash
# Pretty-print all backup-related metrics
curl -s "https://prometheus.soyspray.vip/api/v1/query?query=cnpg_collector_last_available_backup_timestamp" | \
  jq -r '.data.result[] | "\(.metric.cluster // "no-cluster"): \(.value[1] | tonumber | strftime("%Y-%m-%d %H:%M:%S"))"'

# Get time series data (last 1 hour)
curl -s "https://prometheus.soyspray.vip/api/v1/query_range?query=cnpg_collector_last_available_backup_timestamp&start=$(date -u -d '1 hour ago' +%s)&end=$(date -u +%s)&step=300" | \
  jq '.data.result[0].values | map([.[0] | strftime("%H:%M"), .[1]])'
```

### Using `kubectl` + `jq`

```bash
# Get all PrometheusRules with backup alerts
kubectl get prometheusrule -n monitoring -o json | \
  jq '.items[] | select(.spec.groups[].name | contains("backup"))'

# Get PodMonitor details
kubectl get podmonitor -A -o json | \
  jq '.items[] | {name: .metadata.name, namespace: .metadata.namespace, labels: .metadata.labels, port: .spec.podMetricsEndpoints[0].port}'
```

## Key Learnings

### Label Requirements

1. **PrometheusRule** resources MUST have `release: kube-prometheus-stack` label to be discovered by Prometheus
2. **PodMonitor** resources created by operators (like CNPG) won't have the `release` label, so Prometheus needs `podMonitorSelectorNilUsesHelmValues: false`

### CNPG Monitoring Fields

The CNPG Cluster CRD only supports these monitoring fields:
- `enablePodMonitor` (boolean)
- `podMonitorMetricRelabelings` (array)
- `podMonitorRelabelings` (array)
- `customQueriesConfigMap` (array)
- `customQueriesSecret` (array)
- `disableDefaultQueries` (boolean)
- `tls` (object)

**Note**: There is NO `customPodMonitorLabels` field. Labels must be controlled via Prometheus configuration.

### Metric Timestamps

Both metrics return Unix timestamps:
- CNPG: Actual backup completion time
- CronJob: Last successful job completion time

These can be compared with `time()` to calculate staleness in seconds.

## Cost Savings

This monitoring approach has **zero S3 API costs** because:
- CNPG tracks backup timestamps internally (not via S3 listing)
- kube-state-metrics tracks CronJob status from Kubernetes API
- No additional S3 requests are made for monitoring purposes

## Integration with Alertmanager

The alerts automatically integrate with your existing Alertmanager → Telegram setup:
- Alerts fire when backups are >36 hours old
- After 15 minutes in firing state, Alertmanager sends to Telegram
- No additional configuration needed

**Test alerts** (optional):
```bash
# Temporarily modify alert to fire immediately (for testing only)
# Change threshold from "36 * 60 * 60" to "1" in the alert rule
# Don't commit this change!
```

## References

- [CloudNativePG Monitoring Documentation](https://cloudnative-pg.io/documentation/1.20/monitoring/)
- [kube-state-metrics CronJob Metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/cronjob-metrics.md)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/operator/api/)
- [Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/)

