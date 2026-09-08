# Prometheus monitoring

This package prepares the existing Prometheus, Alertmanager, and Grafana stack
for native Argo ownership. It also contains the Prometheus Operator custom
resource definitions (CRDs). No deployment has occurred. Adoption remains blocked
until a completed Longhorn backup and an isolated time-series database (TSDB)
restore provide recovery evidence.

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

The **Soyspray Operations** dashboard has eight panels for node, Argo, Longhorn,
backup, and restore observations. A missing sample means the result is unknown.
A historical restore result does not prove current access.

Alertmanager sends critical and warning alerts to Telegram. The continuous
`Watchdog` alert sends one Healthchecks.io ping each minute. Healthchecks.io can
report a complete monitoring or internet failure.

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

`make deploy APP=prometheus` is blocked because the Prometheus claim has no
completed Longhorn backup or isolated TSDB restore evidence.
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

## Data protection and adoption

Prometheus retains 15 days of metrics in this claim:

`monitoring/prometheus-kube-prometheus-stack-prometheus-db-prometheus-kube-prometheus-stack-prometheus-0`

The claim is a 20 GiB Longhorn volume. Do not change its name, claim binding, or
Prometheus identity during adoption.

This first stage keeps the legacy package and Ansible submission path until
native adoption succeeds and has been verified. Before adoption, complete these
checks:

1. Create a backup of the current Prometheus volume and confirm that it completed.
2. Restore that backup into an isolated claim.
3. Verify that Prometheus can read the restored TSDB.
4. Record the original Application, claim, volume, and Secret identities.
5. Compare the server-rendered workloads, including all dashboards.

During controlled adoption, check each Application UID and confirm that neither
Application has a `deletionTimestamp`. Remove the cascading finalizers from both
existing Applications. Then apply the native root from the pushed branch.

After adoption, verify both Application UIDs, the claim and volume bindings,
metrics history, both access paths, alert delivery, the external watchdog, and all
eight operations panels. Return the native root and the stack source to `HEAD`.

Remove the legacy package, submission role, revision controls, and resolved repair
tasks only in the reviewed cleanup stage.

## Monitoring limits

The backup rules accept only completed Longhorn backups from the volume's current
target. Zero, future, failed, or mismatched timestamps do not qualify. The rules
record backup age and one-hour recovery-point status each minute.

The old-backup alert starts after 45 minutes and waits five minutes. Missing
evidence also alerts after five minutes. These alerts do not prove a successful
restore or continuous seven-day recovery coverage.

The laptop evidence collector remains separate. Its metrics endpoint reports
saved numeric evidence only. It does not run a backup or restore.

Rollback keeps both Applications and all workloads. Restore the previous
Application source and ownership definition through the retained Ansible path.
Do not delete an Application, CRD, claim, volume, namespace, or Secret as rollback.
