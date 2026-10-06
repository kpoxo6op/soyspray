# Immich backup monitoring

The paired backup exports PostgreSQL before collecting required originals every
30 minutes. Restic keeps 48 recent successful and 30 daily snapshots. Snapshot
time is the dump start. Incomplete runs keep the `pending` tag and cannot be
restore candidates.

Use CNPG Backup records, native Job status, and the Restic repository for
recovery-point time and completion. A successful schedule is separate from a
successful isolated restore. There is no laptop observation collector.

The existing `backups-essential` PrometheusRule reads:

- `kube_cronjob_status_last_successful_time` for `immich-paired-backup`.
- `barman_cloud_cloudnative_pg_io_last_available_backup_timestamp` with
  `namespace="postgresql", job="postgresql/immich-db-a"`.

These existing 36-hour stale-backup alerts are coarse health checks. CronJob
completion time is not the recovery-point timestamp. Read the Restic candidate timestamp from its repository; it starts at dump start.

The Barman metric uses the native CNPG exporter on port 9187. The existing
PodMonitor collects it. It replaces the old `cnpg_collector` backup metric.

Use the standard Ansible monitoring source command in the
[recovery README](../../../../../playbooks/operations/recovery). Preserve
Alertmanager delivery when changing queries. Missing metrics are missing
evidence; do not replace them with a successful zero value.
