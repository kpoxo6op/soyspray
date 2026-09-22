# Cluster diagnosis

One operational incident produces one investigation and one Telegram narrative,
with material updates and one recovery message. The loop runs in the cluster, on
DeepSeek, and needs no laptop process.

```text
Alertmanager ──► incident loop ──┬──► Loki        (bounded, allowlisted evidence)
                                 ├──► Jev          (semantic hint, never proof)
                                 ├──► DeepSeek     (one narrative per attempt)
                                 └──► Telegram     (the existing private chat)
Prometheus ◄── /metrics (ServiceMonitor monitoring/cluster-diagnosis)
```

## What runs

| Object | Namespace | Purpose |
| --- | --- | --- |
| `Deployment/cluster-diagnosis` | `monitoring` | The poll loop, one replica, no ServiceAccount token |
| `PersistentVolumeClaim/cluster-diagnosis-state` | `monitoring` | The spend guard and the delivery outbox |
| `Service` + `ServiceMonitor/cluster-diagnosis` | `monitoring` | Its own metrics for Prometheus |
| `NetworkPolicy/cluster-diagnosis` | `monitoring` | Egress only where it must go |

The pod never talks to the Kubernetes API. It has no service account token, and
the NetworkPolicy excludes the pod and service CIDRs, so the API server and every
other workload are unreachable. Calico has no name-based egress rules, so the
external side is "anything outside the cluster CIDRs on 443".

## Incident identity and lifecycle

An incident is one thing a human would investigate.

- A namespaced alert belongs to its application, so several symptoms of one
  failure are one incident.
- A node alert belongs to the node, and a node incident owns the application
  incidents it caused: those start around the node incident and every firing
  symptom names a pod on that node. A consequence does not spend its own
  attempt, and it becomes independent again when the node incident closes. An
  unreadable node-to-pod map merges nothing.
- Anything else falls back to its named resource, then to its alert name.

Only alerts that can page a human are incidents: `critical` and `warning`.
`Watchdog`, `InfoInhibitor` and info-level alerts are ignored. Refresh
timestamps, silences and inhibition do not create an incident. A symptom that
resolves, is inhibited or stops being reported closes after its own grace, and
the incident closes three minutes after its last firing symptom.

Only critical work spends a model call. An incident qualifies when it is critical
itself, or when it is a root incident that owns a critical consequence, which is
what lets one node investigation replace several application investigations. A
warning-only incident is tracked, and it still sends one close message when it
ends, but it never opens a narrative: Alertmanager has already paged the warning
itself and the daily allowance is small.

Only Alertmanager's own resolution is described as recovery. A silence, an
inhibition or a vanished alert is reported as a close with its reason.

## Spending

| Bound | Value | Where |
| --- | --- | --- |
| Attempts per Auckland day | 3 | `DAILY_ATTEMPT_LIMIT` |
| Tokens per Auckland day | 60,000 | `DAILY_TOKEN_LIMIT` |
| Attempts per incident generation | 3 | `incident.MAX_ATTEMPTS_PER_GENERATION` |
| Transmissions per poll | 1 | one candidate per iteration |
| Transmissions per attempt | 1 | retries are scheduled, not repeated |

A reservation for the transmission and its token ceiling is written and
`fsync`ed **before** the request leaves the pod. A request that completes
remotely but is never observed still counts, and a reported usage replaces the
reservation. The provider is asked once per attempt: a 429, a 5xx, a timeout or
an empty answer records the outcome, schedules a bounded `retry_after`, and the
next poll retries it as a separate, charged attempt.

401, 402 and 403 are different: the key is rejected or unfunded, so the loop
stops asking and raises `SoysprayDiagnosisProviderRejected` until the next day.

## The state volume is a ledger, not data

`cluster-diagnosis-state` holds incident identity, the attempt and token ledger,
the delivery outbox and the classifier cache. It has **no disaster-recovery
guarantee and is not backed up**.

- It is written atomically and the process holds an exclusive lock for its whole
  lifetime. The Deployment uses `Recreate`, so two pods cannot write at once.
- A missing file is a normal first start. A corrupt, unreadable or wrong-schema
  file is **not**: model calls stop, readiness reports `state-unusable`, and
  `SoysprayDiagnosisStateUnusable` fires. Losing the ledger would hand back a
  fresh daily allowance, so it fails closed.
- The claim is part of the Application, so ordinary upgrades preserve it.

### Guarded reset

Reset the ledger deliberately, and only when you intend to grant a fresh day:

```sh
kubectl -n monitoring scale deployment/cluster-diagnosis --replicas=0
kubectl -n monitoring wait --for=delete pod -l app.kubernetes.io/name=cluster-diagnosis --timeout=120s
IMAGE="$(kubectl -n monitoring get deployment cluster-diagnosis -o jsonpath='{.spec.template.spec.containers[0].image}')"
kubectl -n monitoring run cluster-diagnosis-reset --rm -it --restart=Never \
  --image="$IMAGE" --command -- python3 /app/diagnosis.py --reset-state
kubectl -n monitoring scale deployment/cluster-diagnosis --replicas=1
```

`--reset-state` refuses to run while another process holds the lock, so the
scale-down is a safety step, not a formality. The reset pod needs the same
volume: add `--overrides` to mount `cluster-diagnosis-state` at `/state` if the
run above reports a missing state root.

## Data that leaves the cluster

The prompt contains exactly four things, bounded to 16 KiB:

1. the incident: anchor, generation and symptoms with allowlisted labels;
2. the sanitized evidence pack;
3. the classifier summary;
4. fixed read-only Prometheus series.

The evidence collector reads only the incident's own namespace and container,
inside a 15-minute window, with aggregate bounds: 6 targets, 120 lines, 512 KiB
per incident, and a 1 MiB cap on any single response. A message leaves the
module only when the fixed signal vocabulary recognises it; free text, personal
records, application payloads and injected instructions stay local and become an
explicit `message-held-back` or `text-format-not-exported` gap. Every query is
built only from charset-validated label values, so alert text can never widen it.

The prompt marks all of it as untrusted data, and the model has no tools, no
cluster access and no way to act.

**Provider terms.** DeepSeek receives the incident payload, and its published
policy describes collection, training-related processing and storage in China.
This is a different processor from the previous OpenAI path, and no
zero-retention agreement is in place. The allowlist is the only control on what
that provider sees, which is why it is strict.

## Delivery

Messages go to the existing private chat through the existing Alertmanager bot,
so a narrative arrives beside the alert it explains. The bot token is mounted
read-only from `monitoring/alertmanager-telegram-secret`; this workload never
creates, changes or deletes that Secret, and the recipient is application
configuration rather than model output.

Delivery is separate from diagnosis: a narrative is queued in the outbox and
sent in the same iteration, a failure is retried on later polls without another
model call, the outbox holds at most 20 entries, and an entry older than six
hours is dropped. Telegram can accept a message before the client gives up, so a
duplicate is possible; a narrative is never sent for an incident that already
recovered.

## Metrics

| Series | Meaning |
| --- | --- |
| `soyspray_diagnosis_up` | The loop is running |
| `soyspray_diagnosis_last_poll_timestamp_seconds` | Last completed poll |
| `soyspray_diagnosis_state_usable` | 0 stops all model calls |
| `soyspray_diagnosis_attempts_today`, `_tokens_today` | Current day against its ceiling |
| `soyspray_diagnosis_provider_blocked` | The provider rejected the key |
| `soyspray_diagnosis_outbox_pending`, `_delivery_total` | Delivery state |
| `soyspray_diagnosis_outcome_total`, `_model_info` | Outcomes and serving model |
| `soyspray_incident_open`, `_opened_timestamp_seconds` | Open incidents |
| `soyspray_evidence_*`, `soyspray_classifier_*` | Evidence and classifier state |

Never-attempted work exposes no series, so the dashboard shows unknown rather
than a false zero. Five alerts cover the failure modes:
`SoysprayDiagnosisStale` (no metrics, or no completed poll for 15 minutes),
`SoysprayDiagnosisSourceUnreadable` (the loop polls but cannot read
Alertmanager, so nothing can be investigated), `SoysprayDiagnosisStateUnusable`,
`SoysprayDiagnosisProviderRejected` and `SoysprayDiagnosisDeliveryBacklog`.

## Models

`DEEPSEEK_PROFILE=flash` is the default: `deepseek-flash` with thinking
explicitly disabled, `max_tokens` 1200, a 60-second deadline. The ceiling is
1200 because a 512-token answer for a full incident payload came back
truncated, which the loop correctly refused to deliver. `reasoning` selects
`deepseek-v4-pro` with thinking enabled, `max_tokens` 4096 and a 90-second
deadline. `DEEPSEEK_MODEL` and `DEEPSEEK_THINKING` override either profile.

An empty or truncated answer is a failure, never a message: a reasoning model
that spends its whole budget before answering produces an explicit
`empty-content` outcome instead of an empty Telegram message.

## Setup

The DeepSeek key lives in an Ansible Vault file outside the repository and is
installed into `monitoring/cluster-diagnosis-deepseek`:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  apps/cluster-diagnosis/bootstrap.yml \
  -e @~/.config/soyspray/recovery/cluster-diagnosis.vault.yml \
  --vault-password-file ~/.config/soyspray/recovery/vault-password
```

The bootstrap refuses to replace an installed key, and it only ever creates its
own Secret. Rotation is a separate reviewed operation: remove the Secret
deliberately, then run the bootstrap with the new key.

Runtime code ships as an immutable GHCR image. A source change opens a separate
digest promotion PR, so a source-only merge never changes running code.

## Checks

```sh
make check APP=cluster-diagnosis
make diff APP=cluster-diagnosis
```

`make restore-check APP=cluster-diagnosis` reports that the ledger has no
restore check on purpose: it is a spending guard, not application data with a
recovery contract.

The tests cover the ledger and its reservations, the provider request shape and
every failure mode, the delivery outbox, the incident lifecycle, evidence gaps,
prompt budgeting, and the metrics exposition.

## Operating

```sh
kubectl -n monitoring logs deploy/cluster-diagnosis --tail=50
kubectl -n monitoring exec deploy/cluster-diagnosis -- python3 /app/diagnosis.py --print-metrics
kubectl -n monitoring rollout restart deploy/cluster-diagnosis
```

`--once` runs a single iteration and exits; it takes the same lock as the running
loop, so it reports `busy` rather than racing it.

## Cutover and rollback

Cutover is complete: the OpenClaw job was removed with
`playbooks/operations/retirement/laptop-cluster-diagnosis.yml`, and the laptop
keeps only backup and restore evidence.

Roll back to the laptop loop:

1. Revert the commit that removed `apps/cluster-diagnosis/install.yml` and the
   runtime installer import.
2. Run `ansible-playbook playbooks/operations/runtime/install.yml -e
   operations_revision=COMMIT -e diagnosis_enabled=true`.
3. Convert the cluster ledger into the laptop schema, or accept a fresh laptop
   day, and note that the two ledgers are independent.

Roll back the provider only:

1. Revert the image digest to the last reviewed one, or set `DEEPSEEK_PROFILE`
   to move to the reasoning profile.
2. If the key must change, remove `monitoring/cluster-diagnosis-deepseek` and
   rerun the bootstrap with the new Vault value.
