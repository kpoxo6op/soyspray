# Scripts

This directory contains utility scripts for the cluster and the Kong bank lab.

## Credential trial

- `agent-secret` reads only `hays-online-timesheets` from Vaultwarden. It needs
  `bw`, `kubectl`, and cluster access. The command prints plaintext credential
  JSON, so do not send its output to logs or GitHub.

```bash
agent-secret read hays-online-timesheets
```

## Kong bank lab

- `banklab_status.py` prints node and Argo application health.
- `banklab_smoke.py` runs read-only route, authentication, exposure, and
  customer-app checks.
- `configure_status_page.py` reconciles the external public status page and
  its DNS-only CNAME. Its `--fallback` switch activates the hosted Better
  Stack address when the custom hostname must be bypassed.
- `validate_skills.py` checks the reusable Agent Skills under `.agents/skills`.
- `validate_openapi_specs.py` validates the six synthetic API contracts.
- `validate_yaml.py` parses the YAML files used by the local quality gate.

The `Makefile` wraps these commands through `make status`, `make smoke`, and
`make check`.

## Cluster utilities

- `ansible-completion.bash` provides Ansible tag completion.
- `argocd-list.sh` lists Argo CD applications for `make list-apps`.
- `check-ha-stretch.sh` checks the one-node-loss stretch configuration.

```sh
scripts/check-ha-stretch.sh --expect-current --repo-only
scripts/check-ha-stretch.sh --expect-ha --repo-only --vip 192.168.20.13
scripts/check-ha-stretch.sh --expect-ha --live --vip 192.168.20.13
```
