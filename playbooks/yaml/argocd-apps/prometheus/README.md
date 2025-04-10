# Prometheus, AlertManager, and Telegram Integration

## Architecture

```text
                                                    ┌─────────────────┐
                                                    │                 │
                                                    │  Telegram Bot   │
                                                    │                 │
                                                    └────────▲────────┘
                                                            │
                                                            │
┌──────────────┐         ┌──────────────┐         ┌────────┴────────┐
│              │         │              │         │                 │
│  Prometheus  ├────────►│ AlertManager ├────────►│ Secret:        │
│              │  Alert  │              │   Uses  │ bot_token      │
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

May take 10 mins to sync in ArgoCD

## Components Overview

### 1. Prometheus Rules

- Located in `alerts/` directory
- Each rule file defines conditions for specific alerts
- Example rules:
  - Temperature monitoring
  - Node status
  - Application metrics

### 2. AlertManager Configuration (values.yaml)

```yaml
alertmanager:
  config:
    route:
      receiver: 'telegram'
      routes:
        - matchers:
          - severity=~"warning|critical"
    receivers:
    - name: 'telegram'
      telegram_configs:
      - bot_token_file: /etc/alertmanager/telegram/TELEGRAM_BOT_TOKEN
        chat_id: 336642153
```

### 3. Telegram Integration (managed by Ansible)

- Bot token stored in .env file
- Ansible creates secret: `alertmanager-telegram-secret`
- Mounted in AlertManager pod

## Flow

1. Prometheus continuously evaluates alert rules
2. When any rule triggers, alert sent to AlertManager
3. AlertManager routes based on severity/labels
4. Notifications sent to Telegram via bot

## Adding New Alerts

1. Create new rule file in `alerts/` directory
2. Add appropriate labels for routing
3. Update kustomization.yaml if needed
4. Test with temporary thresholds

## Maintenance

- Alert rules managed in individual yaml files
- Bot credentials through .env and Ansible
- AlertManager config in values.yaml

## Verification

- Prometheus UI: `/alerts`
- AlertManager: `/alertmanager/config`
- Test new rules by lowering thresholds

## Deletion patch if stuck

If ArgoCD application is stuck:

```sh
kubectl delete ns monitoring
kubectl patch application prometheus -n argocd -p '{"metadata":{"finalizers":null}}' --type=merge
```

### Scenario: Stuck Sync + Resources in 'default' Namespace (April 2025)

If the `kube-prometheus-stack` application gets stuck syncing (often waiting for hooks like `kube-prometheus-stack-admission-create` or showing cluster-scoped resources as `Missing`), and you then observe namespaced resources like the operator deployment or statefulsets appearing in the `default` namespace after attempting fixes, follow these steps:

1. **Verify Core Settings:** Ensure the following settings are correct:
    - In `prometheus-application.yaml` (`spec.syncPolicy.syncOptions`):
        - `CreateNamespace=true`
        - `AllowClusterResourceInNamespacedApp=true` (Crucial for allowing cluster-scoped resources)
    - In `values.yaml`:
        - Top-level `namespaceOverride: monitoring` is **present**. (Ensures Helm *templates* resources into the correct namespace).
        - Under `prometheusOperator.admissionWebhooks.patch`:
            - `hookDeletePolicy: before-hook-creation,hook-succeeded` (Helps cleanup hook jobs).

2. **Terminate Stuck Operation:** If a sync is still stuck from previous attempts:

    ```sh
    argocd app terminate-op kube-prometheus-stack
    ```

3. **Commit & Refresh/Sync:** Commit the verified settings to Git. Trigger a refresh and sync in Argo CD:

    ```sh
    # Optional: Force refresh
    argocd app get kube-prometheus-stack --refresh
    # Trigger sync
    argocd app sync kube-prometheus-stack
    ```

4. **Monitor:** Wait for the sync to complete. Argo CD should create resources in `monitoring` and, if `prune=true`, remove the incorrect ones from `default`.

    ```sh
    argocd app wait kube-prometheus-stack --health
    kubectl get all -n monitoring
    kubectl get all -n default # Should only show 'service/kubernetes'
    ```

**Root Cause:** This situation typically arises if `namespaceOverride` is missing/incorrect in `values.yaml`, causing Helm to template resources into `default`, even if Argo CD's `destination.namespace` is `monitoring`. `AllowClusterResourceInNamespacedApp=true` only helps with *cluster-scoped* resources, not incorrectly namespaced ones.

If namespace is stuck in "Terminating" state:

```sh
# 1. Remove finalizers from pods
kubectl get pod -n monitoring -o json | jq '.items[] | .metadata.name' | xargs kubectl patch pod -n monitoring --type='json' -p='[{"op": "remove", "path": "/metadata/finalizers"}]'

# 2. Remove finalizers from PVCs
kubectl get pvc -n monitoring -o json | jq '.items[] | .metadata.name' | xargs kubectl patch pvc -n monitoring --type='json' -p='[{"op": "remove", "path": "/metadata/finalizers"}]'

# 3. Patch the namespace to remove finalizers
kubectl patch namespace monitoring -p '{"metadata":{"finalizers":null}}' --type=merge

# 4. If still stuck, apply a more comprehensive patch
kubectl patch namespace monitoring -p '{"metadata":{"finalizers":null},"spec":{"finalizers":[]}}' --type=merge

# 5. Force delete all resources in namespace (final resort)
for type in $(kubectl api-resources --namespaced=true --verbs=delete -o name); do kubectl delete ${type} --all -n monitoring --force --grace-period=0; done
```

## Storage Considerations

### Performance Investigation Findings (2025-03-09)

We identified performance issues with the default Prometheus storage configuration:

- Prometheus config loading operations taking minutes instead of milliseconds
- Log evidence: "Completed loading of configuration file... totalDuration=2m54.970655246s"
- Root cause: Using local system disk (mmcblk1p2) with limited I/O capabilities and poor random I/O performance (100-500 IOPS)

This leads to limited data retention, growing query latency, risk of OOM kills, and potential data loss during pod restarts.

### Plan: Longhorn Storage Implementation

To resolve these issues, we will utilize Longhorn for Prometheus storage:

1. Create dedicated Longhorn StorageClass for monitoring data
2. Configure Prometheus with proper storage settings:

```yaml
prometheus:
  prometheusSpec:
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: longhorn-monitoring
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    retention: 15d
    retentionSize: "30GB"
```

### Performance Comparison Methodology

Current Performance Baseline (2025-03-09):

- Previous configuration loading times: 2m54.970655246s and 37.910238741s (from earlier logs)
- Current configuration loading times: 6.988348724s and 9.329987934s (from latest logs)
- WAL replay duration: 28.320963951s during startup
- Actual log evidence:

```
time=2025-03-09T08:59:24.415Z level=INFO source=head.go:832 msg="WAL replay completed" component=tsdb checkpoint_replay_duration=500.335µs wal_replay_duration=28.092787635s wbl_replay_duration=494ns chunk_snapshot_load_duration=0s mmap_chunk_replay_duration=9.666µs total_replay_duration=28.320963951s
time=2025-03-09T08:59:33.151Z level=INFO source=main.go:1482 msg="Completed loading of configuration file" db_storage=6.053µs remote_storage=12.791µs web_handler=4.343µs query_engine=6.087µs scrape=92.285366ms scrape_sd=305.411814ms notify=14.740995ms notify_sd=155.452606ms rules=40.391395ms tracing=41.455µs filename=/etc/prometheus/config_out/prometheus.env.yaml totalDuration=6.988348724s
time=2025-03-09T08:59:42.502Z level=INFO source=main.go:1482 msg="Completed loading of configuration file" db_storage=7.164µs remote_storage=8.791µs web_handler=2.4µs query_engine=5.213µs scrape=684.857938ms scrape_sd=1.55509ms notify=2.538165ms notify_sd=70.185µs rules=1.454693013s tracing=38.823µs filename=/etc/prometheus/config_out/prometheus.env.yaml totalDuration=9.329987934s
```

After Longhorn SSD Implementation:

- Re-run the same configuration loads
- Expected configuration load time: 1-3 seconds (50-100x improvement)
- Expected query response time: 5-10x faster
- Memory usage should remain more stable with fewer spikes

The dramatic difference in configuration load time (from 3 minutes to a few seconds) will directly translate to improved dashboard loading times, alert evaluation speed, and overall system stability.

### How to Retrieve Performance Logs

To get the same performance metrics for future comparison:

```sh
# Get full Prometheus logs
kubectl logs prometheus-kube-prometheus-stack-prometheus-0 -n monitoring -c prometheus

# Filter for configuration loading time specifically
kubectl logs prometheus-kube-prometheus-stack-prometheus-0 -n monitoring -c prometheus | grep "Completed loading of configuration file" | grep "totalDuration"

# Show the last 30 log lines (useful during startup)
kubectl logs prometheus-kube-prometheus-stack-prometheus-0 -n monitoring -c prometheus | tail -n 30
```

When reading the logs, look for lines like:

```
time=2025-03-09T08:44:21.303Z level=INFO source=main.go:1482 msg="Completed loading of configuration file" db_storage=6.083µs remote_storage=9.021µs web_handler=2.456µs query_engine=4.316µs scrape=39.564083824s scrape_sd=5.250933ms notify=8.971657682s notify_sd=125.231µs rules=46.862132152s tracing=37.428µs filename=/etc/prometheus/config_out/prometheus.env.yaml totalDuration=2m54.970655246s
```

The key metric is `totalDuration=2m54.970655246s` which indicates how long Prometheus took to reload its configuration.
