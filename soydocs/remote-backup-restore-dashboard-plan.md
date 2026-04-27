# Remote Backup And Restore Dashboard Plan

## Summary

Build the dashboard inside the existing `kube-prometheus-stack` Grafana
deployment. Do not create a separate Grafana app.

Two implementation tasks are required:

1. Fix Loki datasource provisioning in
   `playbooks/argocd/applications/observability/prometheus/values.yaml` so
   Grafana gets a live `loki` datasource.
2. Add a new GitOps-managed dashboard JSON in
   `playbooks/argocd/applications/observability/prometheus/dashboards/` and
   register it in the Prometheus app kustomization.

Scope for v1 is all remote backups:

- Immich media
- Immich / CNPG database
- Obsidian

"Restore status" in v1 means restore readiness plus recent restore-related Loki
activity, because the cluster does not currently emit a dedicated periodic
restore-success signal.

## Key Changes

### Grafana datasource

- Move the Loki datasource definition from the wrong path under
  `grafana.sidecar.datasources.additionalDataSources` to the chart-supported
  top-level `grafana.additionalDataSources`.
- Provision Loki with fixed UID `loki`, URL
  `http://loki.monitoring.svc.cluster.local:3100`, and proxy access.
- Keep Prometheus as the default datasource.

### Dashboard JSON

- Create a dashboard with fixed UID and title `Remote Backup & Restore Status`.
- Keep it in the default Grafana folder to match current provisioning.
- Use a data-first layout:
  - Hero row with large status cards
  - Per-system backup cards
  - Recent activity and restore-readiness panels

### Loki-backed status model

- Immich media backup success:
  - Kubernetes event stream for `immich-media-offsite-sync`
  - Success markers: `Completed`, `SawCompletedJob`
- Immich media backup failure:
  - Existing `aws-sync` container error query
  - Existing `BackoffLimitExceeded` event query
- Obsidian backup success:
  - `{namespace="obsidian", container="backup"} |= "Backup completed"`
- Obsidian backup failure:
  - Existing error and backoff queries
- CNPG backup success:
  - `{namespace="postgresql"} |= "Completed barman-cloud-backup"`
- CNPG PITR readiness:
  - Recent WAL archive activity from
    `{namespace="postgresql"} |= "Executing barman-cloud-wal-archive"`
  - Fail readiness when recent `barman` or `archive_command` failures match
- Restore activity section:
  - Query restore-related postgresql logs
  - Empty result is acceptable and means no recent restore drill was observed

### GitOps and iteration loop

- Reuse the existing observability Argo app.
- Verify through the Grafana ingress `grafana.soyspray.vip`.
- Use ingress-aware API checks with:

  ```bash
  curl --resolve grafana.soyspray.vip:443:192.168.20.10 \
    https://grafana.soyspray.vip/...
  ```

- Use Playwright against the ingress once local name resolution for
  `grafana.soyspray.vip` works in the agent environment.

## Test Plan

- `kubectl kustomize playbooks/argocd/applications/observability/prometheus >/dev/null`
- Argo app `kube-prometheus-stack` reaches `Synced` and `Healthy`
- Grafana datasources contain `prometheus`, `alertmanager`, and `loki`
- Grafana search returns the new dashboard
- Immich, Obsidian, and CNPG panels each return real Loki data
- Restore panel empty state is treated as acceptable if no restore drill exists
- Playwright visual check through Grafana ingress

## Assumptions

- Reuse the existing Grafana deployment and provisioning pattern
- Keep the dashboard in the default folder
- Store the dashboard as checked-in JSON only
- Interpret "restore status" as restore readiness plus recent Loki activity
