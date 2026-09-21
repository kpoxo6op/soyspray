# Prometheus monitoring

This package defines native Argo ownership for the existing Prometheus,
Alertmanager, and Grafana stack and the Prometheus Operator CRDs. Prometheus
metrics are disposable on this toy cluster. The deployment does not require
backup or restore evidence.

The package keeps these Application identities and versions:

| Application | Source | Version |
| --- | --- | --- |
| `kube-prometheus-stack` | `prometheus-community/kube-prometheus-stack` through Kustomize | `78.2.0` |
| `prometheus-crds` | `prometheus-community/prometheus-operator-crds` | `16.0.1` |

The native definitions use separate AppProjects. The stack project cannot manage
CRDs. The CRD project cannot manage stack resources. Both definitions disable
automated pruning and omit cascading deletion finalizers. Existing live
finalizers must be removed during controlled adoption.

## Normal use

Open Grafana at `https://grafana.soyspray.vip` and sign in through Authentik OIDC.
Open Prometheus at `https://prometheus.soyspray.vip`, which uses Authentik forward
authentication.

The **Soyspray Operations** dashboard has fifteen panels for node, Argo,
Longhorn, backup, restore, incident, collector and classifier observations. A
missing sample means the result is unknown. A historical restore result does not
prove current access.

Alertmanager sends critical and warning alerts to Telegram. The continuous
`Watchdog` alert sends one Healthchecks.io ping each minute. Healthchecks.io can
report a complete monitoring or internet failure.

## Alert ownership

Prometheus owns every health and paging decision. `alerts/runtime-signals.yaml`
carries the rules that replaced the retired Loki ruler rules, including the
Alloy-derived log and event counters.
[apps/loki/manifests/docs/ALERT-PIPELINE.md](../loki/manifests/docs/ALERT-PIPELINE.md)
holds the complete mapping, the detection timing and the missing-evidence
behaviour.

The Telegram template is plain text on purpose, and `parse_mode: ""` is set
explicitly because Alertmanager defaults an absent `parse_mode` to `HTML`. With
HTML, one unescaped `<` in alert text made Telegram reject a whole group with
`can't parse entities` (96 rejected deliveries on 2026-09-13), so a critical
alert could be lost. The template trims the label set and renders at most twelve
alerts per group, then says how many were left out, so a group stays inside the
Telegram message limit. Annotations themselves remain unbounded, so a single
alert with an extremely long annotation could still exceed it.

`SoysprayLogPipelineStalled` covers the evidence path: it warns when an Alloy
instance is up but has sent nothing to Loki for 20 minutes, so a silent log
pipeline is visible before the next incident needs log evidence.

Node-level inhibition is not used. The standard kube-state-metrics alerts carry
no `node` label, so an inhibition rule with `equal: [node]` could not match them.
The laptop incident adapter instead correlates a node incident with its
application consequences using `kube_pod_info`, and stops diagnosing those
consequences separately.

## Commands

Run the focused checks:

```sh
make check APP=prometheus
```

Compare the complete local package with the live stack. This comparison includes
JSON dashboards and does not sync resources:

```sh
make diff APP=prometheus
```

Read the primary Application, runtime, storage, and recovery evidence:

```sh
make status APP=prometheus FORMAT=json
```

Merge the pull request to deploy through the native root.
`make restore-check APP=prometheus` reports that no maintained isolated TSDB
restore check exists.

## Alert identity recovery

The deployment uses the existing `alertmanager-telegram-secret` Secret.
Bootstrap reads and preserves it, and creates it only when it is missing.
Bootstrap cannot update or rotate an existing token.

Supply a missing token through an encrypted Ansible variables file:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu apps/prometheus/bootstrap.yml \
  -e @/path/to/prometheus-recovery.vault.yml \
  --vault-password-file /path/to/vault-password
```

The encrypted file must define `prometheus_telegram_bot_token`. Keep the token and
Vault password outside Git.

Authentik owns the existing `grafana-oidc` Secret. Use the Authentik procedure to
recover or change that identity.

## Data and adoption

Prometheus retains 15 days of metrics in this claim:

`monitoring/prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0`

The claim is a 20 GiB Longhorn volume. Adoption does not intentionally change the
claim name, binding, or Prometheus identity. Loss of metrics history is accepted.
Recovery is not verified.

The native definitions disable automated pruning and protect both Applications
from root pruning and deletion. The monitoring namespace and Prometheus claim are
not added to native ownership.

The legacy package, adoption operation, and Ansible submission path are removed.

After adoption, verify both Application UIDs, sources, projects, and health. Check
the claim and volume identities without treating them as recovery evidence. Check
both access paths, Alertmanager, the external watchdog, and all eight operations
panels. The native root and stack source follow `main`.

## Monitoring limits

The backup rules accept only completed Longhorn backups from the volume's current
target. Zero, future, failed, or mismatched timestamps do not qualify. The rules
record backup age and one-hour recovery-point status each minute.

The old-backup alert starts after 45 minutes and waits five minutes. Missing
evidence also alerts after five minutes. These alerts do not prove a successful
restore or continuous seven-day recovery coverage.

The laptop evidence collector remains separate. Its metrics endpoint reports
saved numeric evidence only. It does not run a backup or restore.

Revert the faulty change through GitHub. Verify both Applications are Synced and
Healthy after the revert reaches `main`. Do not delete Applications,
CRDs, claims, volumes, namespaces, or Secrets during rollback. Backup and restore
are unsupported; rollback cannot recover lost metrics.
