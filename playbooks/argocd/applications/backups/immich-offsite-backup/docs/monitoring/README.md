# Immich backup monitoring

The paired backup exports PostgreSQL before collecting required originals every
30 minutes. Restic keeps 48 recent successful and 30 daily snapshots. Snapshot
time is the dump start. Incomplete runs keep the `pending` tag and cannot be
restore candidates.

Use `make backup-status FORMAT=json` and the native operations evidence timer
for recovery-point age and restore evidence. The collector records real
observations; it does not backfill missing samples. A successful schedule is
not proof that content can be restored.

The existing `backups-essential` PrometheusRule reads:

- `kube_cronjob_status_last_successful_time` for `immich-paired-backup`.
- `barman_cloud_cloudnative_pg_io_last_available_backup_timestamp` with
  `namespace="postgresql", job="postgresql/immich-db-a"`.

These existing 36-hour stale-backup alerts are coarse health checks. CronJob
completion time is not the recovery-point timestamp. The native evidence
collector uses the Restic candidate timestamp, which comes from dump start.

The Barman metric uses the native CNPG exporter on port 9187. The existing
PodMonitor collects it. It replaces the old `cnpg_collector` backup metric.

Use the standard Ansible monitoring source command in the
[recovery README](../../../../../../operations/recovery/README.md). Preserve
Alertmanager delivery when changing queries. Missing metrics are missing
evidence; do not replace them with a successful zero value.
