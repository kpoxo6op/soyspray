# Grafana Loki + Grafana Alloy

This application deploys a single-binary Grafana Loki instance with persistent
storage alongside Grafana Alloy agents that run on every node. It collects
cluster-wide pod logs and Kubernetes events, derives bounded Prometheus signal
counters, and keeps every raw line searchable from Grafana.

Loki does not decide when to page. The Loki ruler is retired, and Prometheus now
owns all health and paging rules. See
[manifests/docs/ALERT-PIPELINE.md](manifests/docs/ALERT-PIPELINE.md) for the
pipeline, the counter list, and the rule mapping.

Alertmanager routes and groups alerts. Critical and warning alerts go to
Telegram, and the continuous `Watchdog` alert pings Healthchecks.io.

## Normal use

- Query raw logs in Grafana with the Loki data source.
- Read the derived signals with
  `sum by (namespace, container) (increase(soyspray_log_media_backup_failure_total[1h]))`.
- Confirm the pipeline is live with `loki_write_sent_bytes_total` and
  `up{job="monitoring/alloy"}`. `SoysprayLogPipelineStalled` warns when an Alloy
  instance stops sending while it is still up.

## Commands

```sh
make check APP=loki
make diff APP=loki
make status APP=loki FORMAT=json
```

`make check APP=loki` validates YAML and renders the Kustomize package. Loki has
no maintained isolated restore check; `make restore-check APP=loki` reports that
honestly and exits non-zero.

## Retention and change limits

- Loki keeps 48 hours of logs on a Longhorn-backed filesystem volume, with
  compactor retention enabled. A longer window needs more storage first.
- Adding a label in the Alloy pipeline changes the stored stream identity and
  doubles the streams for the affected lines. Prefer a new counter name over a
  new stream label.
- Rule changes belong in `apps/prometheus/config/alerts/`, never in a Loki rules
  ConfigMap.

## Why manual deployment

Currently using manual deployment instead of operators because the Loki operator
requires S3-compatible object storage. Migration to the operator approach is
tracked in:

- <https://github.com/kpoxo6op/soyspray/issues/83> (Install more RAM)
- <https://github.com/kpoxo6op/soyspray/issues/84> (Deploy MinIO object storage)
- <https://github.com/kpoxo6op/soyspray/issues/85> (Migrate to operators)
