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

*Note: The Healthchecks.io check is configured with a Period of ~2 minutes and a Grace Time of ~1 minute to match the AlertManager `repeat_interval`.*

## Monitored Components

| Component | Method | Notes |
|-----------|--------|-------|
| **Kubernetes Core** | ServiceMonitor | API Server, Kubelet, Controller Manager, Scheduler, CoreDNS |
| **Node Metrics** | Node Exporter | CPU, Memory, Disk, Network for all nodes |
| **Cluster State** | Kube State Metrics | Deployment status, Pod phases, etc. |
| **ArgoCD** | ServiceMonitor | Application sync status and health |
| **Cert-Manager** | ServiceMonitor | Certificate expiration and renewal status |
| **Prometheus Stack** | ServiceMonitor | Self-monitoring of Prometheus, AlertManager, Grafana |

## Alerting

Alerts are routed based on severity:

*   **Critical/Warning**: Sent to Telegram via a custom template.
*   **Watchdog**: Sent to Healthchecks.io (Dead Man's Switch).
*   **Info/Other**: Suppressed or logged.
