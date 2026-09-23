# Prometheus monitoring

This package defines native Argo ownership for the existing Prometheus,
Alertmanager, and Grafana stack, its disposable dashboards and custom rules,
and the Prometheus Operator CRDs. Prometheus
metrics are disposable on this toy cluster. The deployment does not require
backup or restore evidence.

The package keeps these Application identities and versions:

| Application | Source | Version |
| --- | --- | --- |
| `kube-prometheus-stack` | `prometheus-community/kube-prometheus-stack` through Kustomize | `78.2.0` |
| `prometheus-crds` | `prometheus-community/prometheus-operator-crds` | `16.0.1` |
| `prometheus-config` | `apps/prometheus/config` | `main` |

The native definitions use separate AppProjects. The stack project cannot manage
CRDs. The CRD project cannot manage stack resources. The configuration project
permits only ConfigMaps and PrometheusRules in `monitoring`. The stack and CRD
Applications disable automated pruning. The configuration child prunes obsolete
dashboards and custom rules. All three Applications omit cascading deletion
finalizers and are protected from root pruning and deletion.

## Normal use

Open Grafana at `https://grafana.soyspray.vip` and sign in through Authentik OIDC.
Open Prometheus at `https://prometheus.soyspray.vip`, which uses Authentik forward
authentication.

The **Soyspray Operations** dashboard has twelve panels for node, Argo,
Longhorn, backup, restore, incident, evidence and delivery observations. A
missing sample means the result is unknown. A historical restore result does not
prove current access.

Alertmanager sends critical and warning alerts to Telegram. The continuous
`Watchdog` alert sends one Healthchecks.io ping each minute. Healthchecks.io can
report a complete monitoring or internet failure.

## Alert ownership

Prometheus owns every health and paging decision. `config/alerts/runtime-signals.yaml`
carries the rules that replaced the retired Loki ruler rules, including the
Alloy-derived log and event counters. `config/alerts/cluster-diagnosis.yaml` covers the factual incident loop:
`SoysprayDiagnosisStale` (no metrics or completed poll),
`SoysprayDiagnosisSourceUnreadable` (Alertmanager read failures),
`SoysprayDiagnosisStateUnusable` (incident or delivery state unreadable), and
`SoysprayDiagnosisDeliveryStalled` (oldest queued update above thirty minutes).
[apps/loki/manifests/docs/ALERT-PIPELINE.md](../loki/manifests/docs/ALERT-PIPELINE.md)
holds the complete mapping, the detection timing and the missing-evidence
behaviour.

The [configuration folder](config/README.md) owns the generated dashboard
ConfigMaps and custom rules. Dashboard names are stable: changing a JSON file
updates its existing ConfigMap. Removing or reverting a file causes the
configuration child to prune only that disposable object. The stack chart's
own rules and ConfigMaps remain with the non-pruning stack Application.

The Telegram template may use only Go `text/template` builtins plus the
functions Alertmanager adds (`date`, `humanizeDuration`, `join`, `match`,
`reReplaceAll`, `safeHtml`, `since`, `stringSlice`, `title`, `toLower`,
`toUpper`, `trimSpace`, `tz`). There is no arithmetic and no substring function,
so the overflow line reports the group size and the number shown, and length
bounds come from `reReplaceAll`. An undefined function fails the reload and
raises `AlertmanagerFailedReload` while the old configuration keeps running, so
`apps/loki/tests/test_alloy_signals.py` rejects any unknown name.

`parse_mode` stays at Alertmanager's `HTML` default. An empty value would
disable entity parsing, but the Prometheus Operator omits an empty string from
the generated config, so asking for it changes nothing and only looks effective.

The failure mode being defended against is truncation, not escaping. In HTML
mode the engine auto-escapes alert text, but Alertmanager cuts the rendered
message at 4096 runes, and a cut inside an escaped entity leaves the message
unparseable, so Telegram rejects the whole group. That is what produced the 96
rejected deliveries on 2026-09-13. The template therefore removes `<` and `&`
from every long field, caps each field, and renders at most four alerts per
group, which keeps the worst case near 3.6 thousand runes.

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

Compare both local monitoring packages with their live Applications. This
includes dashboard JSON and custom rules and does not sync resources:

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

The stack and CRD definitions disable automated pruning. Root pruning and
deletion remain disabled for all three Applications. The monitoring namespace
and Prometheus claim are not added to the configuration child.

The legacy package, adoption operation, and Ansible submission path are removed.

After adoption, verify all three Application UIDs, sources, projects, and health. Check
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

Revert the faulty change through GitHub. Verify all three Applications are Synced and
Healthy after the revert reaches `main`. Do not delete Applications,
CRDs, claims, volumes, namespaces, or Secrets during rollback. Backup and restore
are unsupported; rollback cannot recover lost metrics.
