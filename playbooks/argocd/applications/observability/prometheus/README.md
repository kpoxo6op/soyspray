# Prometheus, AlertManager, and Healthchecks.io Integration

This directory contains the GitOps configuration for the Prometheus observability stack.

## Architecture Overview

The monitoring pipeline is designed to be robust and self-monitoring ("Watchdog" pattern).

```text
                                                  ┌─────────────────┐
                                                  │                 │
                                          ┌──────►│  Telegram Bot   │
                                          │       │                 │
                                          │       └─────────────────┘
                                          │
┌──────────────┐         ┌──────────────┐ │       ┌─────────────────┐
│              │         │              │ │       │                 │
│  Prometheus  ├────────►│ AlertManager ├─┼──────►│ Healthchecks.io │
│              │  Alert  │              │         │                 │
└──────┬───────┘         └──────┬───────┘         └─────────────────┘
       │                        │
       │ Scrapes                │ Reads
       ▼                        ▼
┌──────────────┐         ┌──────────────┐
│ ServiceMonitors        │ Secret:      │
│ PodMonitors            │ bot_token    │
└──────────────┘         └──────────────┘

```

## Watchdog & Healthchecks.io Integration

We use a "Dead Man's Switch" pattern to monitor the monitoring system itself. This ensures you get notified even if the entire cluster goes offline or cannot send alerts.

1.  **Prometheus** fires a `Watchdog` alert continuously (always firing).
2.  **AlertManager** receives this alert and routes it to a special receiver `watchdog-healthchecks`.
3.  **AlertManager** sends a webhook "ping" every 1 minute to **Healthchecks.io**.
4.  **Healthchecks.io** expects this ping. If it stops arriving (because Prometheus is down, AlertManager is broken, or the cluster lost internet), Healthchecks.io notifies you via email/Telegram.

### Configuration

In `values.yaml`, the webhook URL connects to our specific check:

```yaml
url: "https://hc-ping.com/ee92de78-bf59-4cb8-a41a-01382feb9a65"
```

This UUID corresponds to the check configured in the Healthchecks.io dashboard:

![Healthchecks.io Dashboard Config](https://healthchecks.io/checks/ee92de78-bf59-4cb8-a41a-01382feb9a65/details)

*Note: The Healthchecks.io check is configured with a Period of ~2 minutes and a Grace Time of ~1 minute. The Watchdog Alertmanager route sets both `group_interval` and `repeat_interval` to 1 minute so this cadence is not stretched by the default alert grouping interval.*

## Monitored Components

| Component | Method | Notes |
|-----------|--------|-------|
| **Kubernetes Core** | ServiceMonitor | API Server, Kubelet, Controller Manager, Scheduler, CoreDNS |
| **Node Metrics** | Node Exporter | CPU, Memory, Disk, Network for all nodes |
| **Disk SMART Health** | smartctl_exporter | SMART status, temperatures, pending sectors, NVMe wear |
| **Cluster State** | Kube State Metrics | Deployment status, Pod phases, etc. |
| **ArgoCD** | ServiceMonitor | Application sync status and health |
| **Cert-Manager** | ServiceMonitor | Certificate expiration and renewal status |
| **Prometheus Stack** | ServiceMonitor | Self-monitoring of Prometheus, AlertManager, Grafana |

## Alerting

Alerts are routed based on severity:

*   **Critical/Warning**: Sent to Telegram via a custom template.
*   **Watchdog**: Sent to Healthchecks.io (Dead Man's Switch).
*   **Info/Other**: Suppressed or logged.

## Longhorn backup timestamps

The existing kube-state-metrics service reads Longhorn Backup and Volume
objects. It exports `soyspray_longhorn_backup_snapshot_timestamp_seconds`
and `soyspray_longhorn_volume_info`. The timestamp is the source snapshot
start time. A missing or invalid timestamp does not become zero.

Prometheus rejects backup samples with an error and removes the temporary
error label before storage. A restore candidate must also have
`state="Completed"`, `progress="100"`, a positive timestamp no later than now,
and the same backup target as its volume. Select protected volumes through
`critical_group="enabled"` and `pv_status="Bound"`; use their namespace and
claim labels for display. Do not treat a missing series as a healthy backup.

After `make go`, use the standard Prometheus Ansible deployment with
`-e prometheus_target_revision=<reviewed-branch>` for branch validation.
After merge, use `-e prometheus_target_revision=HEAD` and repeat the operation.
Check that kube-state-metrics remains available and compare the timestamps
with the Longhorn Backup objects. These raw metrics do not by themselves
prove seven days of coverage or a successful restore.

## Critical recovery evidence

`alerts/critical-backups.yaml` records the snapshot time, age, observation status,
and one-hour recovery-point target each minute. It selects bound Longhorn volumes
in the `critical` backup group. Only completed, 100 percent backups from the
volume's current target can qualify. The collector filters backup errors before
storage. Future and zero timestamps do not qualify.

A missing backup or collector leaves age and target status unknown. The observation
metric becomes zero. Raw volume inventory is retained in the rule query for 24
hours so a lost collector still identifies affected claims. After that, the global
inventory alert remains active. An intentional change to the critical group can
therefore leave an evidence warning for up to one day.

The old-backup alert starts after the snapshot is more than 45 minutes old for
five minutes. Missing evidence also alerts after five minutes. Existing Alertmanager
routing sends critical alerts to Telegram. These alerts prove neither a completed
restore nor seven days of recovery coverage. Review continuous observations and
restore results before accepting the policy. Prometheus retains 15 days of data.

Run `make prometheus-check` for native Prometheus rule checks and recovery behavior
tests. The full local and shared CI checks include this command. It uses Prometheus
3.6.0's upstream `promtool`, cached locally after a SHA-256 checked download.
Fixtures are in `tests/critical-backups.yaml` beside this application's manifests.
