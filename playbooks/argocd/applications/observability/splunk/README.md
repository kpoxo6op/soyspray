# Splunk (Standalone + REST Dashboard Pipeline)

This app deploys a single-node Splunk Enterprise instance with:

1. License acceptance enabled at container start.
2. Hardcoded experimental credentials for the built-in `admin` user.
3. A hardcoded sample service account user named `svc_dashboards`.
4. A sample app named `soyspray_dashboards`.
5. Three example Dashboard Studio dashboards managed through Splunk's REST API.

## Hardcoded Credentials

- Splunk admin: `admin` / `AdminPassword123!`
- Dashboard service account: `svc_dashboards` / `ServiceDashboards123!`

These are intentionally hardcoded because this deployment is explicitly experimental.

## Access

- Web UI: `http://splunk.soyspray.vip`
- In-cluster management API: `https://splunk.splunk.svc.cluster.local:8089`

## Dashboard Pipeline

The pipeline lives in `pipeline/splunk_dashboard_pipeline.py` and supports:

- Creating or updating the sample app through `/services/apps/local`
- Creating or updating the service account through `/services/authentication/users`
- Applying dashboards through `/servicesNS/{owner}/{app}/data/ui/views`
- Exporting dashboards back to code so UI-created dashboards can be saved into the repo later

Example local usage:

```bash
python playbooks/argocd/applications/observability/splunk/pipeline/splunk_dashboard_pipeline.py \
  export-all \
  --base-url https://splunk.splunk.svc.cluster.local:8089 \
  --username admin \
  --password AdminPassword123! \
  --owner svc_dashboards \
  --app soyspray_dashboards \
  --dashboard-dir playbooks/argocd/applications/observability/splunk/dashboards
```

## Tests

Run the pipeline tests with:

```bash
python -m unittest discover -s playbooks/argocd/applications/observability/splunk/tests -p 'test_*.py'
```
