# Scripts

This directory contains cluster checks and operator helpers.

## Credential trial

- `agent-secret` signs in as the dedicated Vaultwarden automation account and
  reads only `hays-online-timesheets`. It needs `bw`, `kubectl`, and cluster
  access. The command prints plaintext credential JSON, so do not send its
  output to logs or GitHub. It never uses the human master password.
- `hays-open-submitted-timesheet` uses that item to sign in to Hays and open
  the newest submitted-timesheet details page. It uses a separate Chrome
  profile and prints only the received date. It does not edit or submit a
  timesheet.

```bash
agent-secret read hays-online-timesheets
scripts/hays-open-submitted-timesheet
```

## Checks and public status

- `configure_status_page.py` manages the external public status page and its
  DNS-only CNAME. Its `--fallback` switch activates the hosted Better Stack
  address when the custom hostname must be bypassed.
- `validate_skills.py` checks the Agent Skills under `.agents/skills`.
- `check_prometheus.py` checks native monitoring rules and backup behavior with
  pinned upstream `promtool`. Use `make prometheus-check`.
- `validate_yaml.py` parses the YAML files used by the local quality gate.
- `ci_scope.py` selects affected browser checks for GitHub CI. Shared checks
  always run; [manual dispatch](../.github/workflows/README.md) runs all checks.

Use `make status-page-check` to validate the external status configuration,
`make status-page` to apply it, and `make check` for the full local gate.

## Cluster utilities

- `ansible-completion.bash` provides Ansible tag completion.
- `app_status.py` reads Application ownership, source revisions, and available
  status through `kubectl`. Use `make apps` or `make status APP=boys FORMAT=json`.
  Missing metadata and evidence appear as `unknown` with a cause. API failures
  return a nonzero exit code. See [application operations](../apps/README.md).
- `argo_preview.py` prepares native root parameters for a pushed application branch.
  Use it through [the Argo bootstrap operation](../argocd/README.md#preview-one-adopted-application).
- `make list-apps` uses native `kubectl` output for Argo sync and health.
- `backup_status.py` reads native backup records for `make backup-status`.
  See [recovery operations](../playbooks/operations/recovery/README.md#read-backup-status)
  for coverage and evidence limits.
- `check-ha-stretch.sh` checks the one-node-loss stretch configuration.

```sh
scripts/check-ha-stretch.sh --expect-current --repo-only
scripts/check-ha-stretch.sh --expect-ha --repo-only --vip 192.168.20.13
scripts/check-ha-stretch.sh --expect-ha --live --vip 192.168.20.13
```
