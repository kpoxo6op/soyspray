# Observability pipeline

Prometheus owns every health and paging decision. Alertmanager routes and groups
alerts. Loki stores searchable raw evidence. Alloy collects and derives bounded
event and log signals.

```text
pod logs ──► Alloy DaemonSet ──┬─► Loki  (raw, searchable, 48h)
                               └─► Alloy /metrics (bounded signal counters)
Kubernetes events ──► Alloy events Deployment ──┬─► Loki (raw events)
                                                └─► Alloy /metrics
kube-state-metrics ────────────────────────────────► Prometheus
Alloy /metrics ──► Prometheus (PodMonitor monitoring/alloy, 30s)
Prometheus rules ──► Alertmanager ──► Telegram / Healthchecks.io
Alertmanager ──► cluster incident loop ──► bounded Loki evidence ──► factual update when new
```

## Where a decision is made

| Decision | Owner | Object |
| --- | --- | --- |
| Is a pod crash looping | Prometheus | `SoysprayPodCrashLooping` (critical) |
| Did a volume attach fail | Prometheus | `SoysprayVolumeMountFailure` (critical) |
| Did a backup tool report failure | Prometheus | `SoysprayBackupToolFailure` (warning) |
| Did a database backup or WAL archive fail | Prometheus | `SoysprayDatabaseBackupFailure` (critical) |
| Did a backup job exceed its backoff limit | Prometheus | `SoysprayBackupJobBackoff` (warning) |
| Does a backup record go stale | Prometheus | `CriticalBackupGettingOld`, `ImmichMediaBackupStale`, `CNPGBackupStale` |
| Who receives an alert, and how it is grouped | Alertmanager | `apps/prometheus/values.yaml` |
| What the raw line said | Loki | LogQL queries in Grafana |
| Is there a new supported incident observation | cluster incident loop | `apps/cluster-diagnosis` |

The Loki ruler is retired. Loki no longer holds alert rules, so a Loki restart
cannot stop paging and a rule change cannot silently live in two places.

## Alloy signal counters

The counters come from `loki.process` `stage.metrics` blocks. The metric name
carries the signal, because metric labels come from the log stream and adding a
`signal` label would change the stored stream identity.

Prometheus reads a non-zero value inside a window
(`max_over_time(metric[10m]) > 0`) rather than `increase()`. Alloy creates a
counter on its first match, so the first sample is already `1` and there is no
zero sample to measure an increase from. `increase()` would miss a single
one-shot failure, which is exactly what the backup-job rules must catch.

| Counter | Source | Replaces |
| --- | --- | --- |
| `soyspray_log_media_backup_failure_total` | immich `aws-sync` | `ImmichMediaBackupFailureImmediate` |
| `soyspray_log_couchdb_backup_failure_total` | obsidian `backup` | `ObsidianBackupFailureImmediate` |
| `soyspray_log_database_backup_failure_total` | postgresql barman error lines | `CNPGBackupBarmanError` |
| `soyspray_log_database_archive_failure_total` | postgresql `archive_command` failures | `CNPGWalArchiveFailure` |
| `soyspray_event_mount_failure_total` | warning events | `VolumeMountAttachFailures` |
| `soyspray_event_job_backoff_total` | `BackoffLimitExceeded` events | `ImmichMediaBackupBackoffLimitExceeded`, `ObsidianBackupBackoffLimitExceeded` |

The counters carry only stream labels: `namespace`, `pod`, `container`, `job`,
`cluster`, and for events the `kubernetes_event_*` labels. They exist only while
a matching stream is active, bounded by `max_idle_duration = "1h"`, so the
`/metrics` endpoint cannot grow without limit. The `stage.metrics` blocks stay
last in each pipeline because a later stage can add unexpected metric labels.

A counter is created on its first match, so an absent counter means "no match
yet", not "the pipeline is broken". There is deliberately no always-on counter:
a `match_all` counter would carry a label set per pod or per event object for
the whole Prometheus retention period.

The counter holds its value while its stream stays active, bounded by
`max_idle_duration = "1h"`, so a failure alert stays visible for about an hour
after the last matching line, then Prometheus marks the series stale and the
alert resolves.

Pipeline liveness therefore uses the Alloy writer series that already exist:

- `loki_write_sent_bytes_total` per Alloy instance, consumed by the
  `SoysprayLogPipelineStalled` rule;
- `up{job="monitoring/alloy"}` and `TargetDown` for scrape health.

The selectors themselves are checked against live Loki with
`/loki/api/v1/query_range`, so a selector that cannot parse or cannot match is
found without waiting for a real failure.

## Retired rules

`ApplicationErrorBurst` and `BackupErrorBurst` counted lines containing `error`
or `fatal`. They are removed, and their detection is not replaced one-for-one. A
raw error word is not an operational fact, and the two rules were the only
warning-level signals in this file with no user-visible meaning. A long-running,
Ready application that emits sustained errors but never crashes now produces no
alert from this file; it is visible in Grafana and in bounded cluster evidence, not as a page. The eight specific rules above keep their replacement.
Actionable failures stay detectable through:

- kube-state-metrics rules: `KubePodCrashLooping`, `KubePodNotReady`,
  `KubeContainerWaiting`, `KubeJobFailed`, `KubeDeploymentReplicasMismatch`;
- node rules: `KubeNodeNotReady`, `KubeletDown`, `node-hardware`;
- storage rules: `KubePersistentVolumeErrors`, `KubePersistentVolumeFillingUp`,
  `CriticalBackupGettingOld`, `CriticalBackupEvidenceMissing`;
- the specific backup counters above.

Detection timing is close to the retired rules, with three deliberate
differences:

- The crash-loop rule reads a container waiting state instead of an event line
  and uses a 10-minute lookback instead of 5 minutes, so an init-container crash
  loop is not covered by it.
- The Obsidian backup rule alerts after 1 minute instead of 2.
- `SoysprayVolumeMountFailure` keeps the event object name under
  `kubernetes_event_involved_object_name` rather than a normalized `pod` label.
  The cluster incident loop reads that label when it selects bounded evidence.

## Missing evidence

- Alloy down: `up{job="monitoring/alloy"} == 0` and `TargetDown`.
- Alloy up but not writing: `SoysprayLogPipelineStalled`, which fires roughly
  30 minutes after traffic stops, because the window is 20 minutes and the
  `for:` duration is 10.
- Loki down: Prometheus rules keep working, because no rule reads Loki. The
  incident loop records a collector gap instead of claiming health.
- Alertmanager down: Prometheus keeps evaluating rules; the incident loop reports a source failure in metrics and retries the read.
- Counter never matched: no alert, and no false claim of health. The rule is
  absent, not green.
