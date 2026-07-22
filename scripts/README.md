# Scripts

This directory contains utility scripts for the cluster and the Kong bank lab.

## Kong bank lab

- `banklab_status.py` prints node and Argo application health.
- `banklab_smoke.py` runs read-only route, authentication, exposure, and
  customer-app checks.
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
