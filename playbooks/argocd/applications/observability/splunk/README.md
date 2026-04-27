# Splunk (HTTPS + Operator-Driven REST Pipeline)

This app deploys a bare single-node Splunk Enterprise instance over HTTPS.
It does not create the sample app, service account, or dashboards during Argo
sync. Operators create and manage those objects later by running Python from the
repo.

## Source Of Truth

All Splunk credentials and operator settings live in a local `.env` file in
this directory. The repo includes `.env.example`; copy it to `.env` and replace
the placeholder passwords before deploying or running operator commands.

The local `.env` file is used for:

- Kubernetes deployment configuration through Kustomize `secretGenerator`
- Local operator commands
- Real end-to-end tests

## Access

- Web UI: `https://splunk.soyspray.vip`
- Management API for operator runs: port-forwarded locally by the operator tool

## Human Operator Workflow

Run [manage_splunk.py](//home/boris/code/soyspray/playbooks/argocd/applications/observability/splunk/pipeline/manage_splunk.py).
It reads `.env`, waits for the live Splunk pod, port-forwards directly to the
ready pod, and manages dashboards over the real REST API.

Commands:

```bash
python playbooks/argocd/applications/observability/splunk/pipeline/manage_splunk.py apply
python playbooks/argocd/applications/observability/splunk/pipeline/manage_splunk.py export-all
python playbooks/argocd/applications/observability/splunk/pipeline/manage_splunk.py reset
python playbooks/argocd/applications/observability/splunk/pipeline/manage_splunk.py e2e
```

What each command does:

- `apply`
  Creates or updates the service account, sample app, and dashboards from code.
- `export-all`
  Pulls dashboards from Splunk back into the repo format so UI-created changes
  can be saved as code.
- `reset`
  Deletes the managed app and service account so Splunk returns to a clean,
  pipeline-free state.
- `e2e`
  Runs a real server test: reset, apply, verify over REST, and export back.

## Real E2E Test

Run the live-server test with:

```bash
python playbooks/argocd/applications/observability/splunk/tests/e2e_real.py
```
