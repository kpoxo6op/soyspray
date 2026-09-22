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
the NetworkPolicy excludes the pod CIDR, the service CIDR and the LAN subnet, so
the API server, the node addresses, the router and every other workload are
unreachable. Calico has no name-based egress rules, so the external side is
"anything outside those ranges on 443". Two allowances are wider than they look
and are deliberate: the DNS rule names the node-local cache address on port 53,
and the monitoring rule allows ports 3100, 9090 and 9093 to every pod in the
`monitoring` namespace, because a policy cannot name a Service.

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
`fsync`ed **before** the request leaves the pod. A request whose answer never
arrived keeps its reservation: the provider may have served and billed it, and
only a reported usage figure replaces the reservation, including a reported
zero. The provider is asked once per attempt: a 429, a 5xx, a timeout or an
empty answer records the outcome, schedules a bounded `retry_after`, and the
next poll retries it as a separate, charged attempt.

An attempt that is interrupted with its process is not a lost incident. The
record carries the moment the request started, and a later poll treats an
attempt that outlived its own deadline as abandoned and retries it as a charged
attempt. `SoysprayDiagnosisUndiagnosed` fires when an open critical incident has
had no successful answer for an hour, whichever of these causes applies.

401, 402 and 403 are different: the key is rejected or unfunded, so the loop
stops asking and raises `SoysprayDiagnosisProviderRejected` until the next day.

## The state volume is a ledger, not data

`cluster-diagnosis-state` holds incident identity, the attempt and token ledger,
the delivery outbox and the classifier cache. It has **no disaster-recovery
guarantee and is not backed up**.

- It is written atomically and the process holds an exclusive lock for its whole
  lifetime. The Deployment uses `Recreate`, so two pods cannot write at once.
- A missing file is a normal first start. A corrupt, unreadable or wrong-schema
  file is **not**: model calls stop, nothing is delivered, readiness reports
  `state-unusable`, and `SoysprayDiagnosisStateUnusable` fires. The loop never
  writes over a ledger it could not read, because that would destroy the
  evidence and hand back a fresh daily allowance. It retries the read on every
  poll, so repairing or replacing the file resumes work without a restart.
- The claim is part of the Application, so ordinary upgrades preserve it.

### Guarded reset

Reset the ledger deliberately, and only when you intend to grant a fresh day.
The writer must be stopped first, and Argo CD with automated self-heal will put
a scaled-down Deployment straight back, so park it through Git:

1. Merge a one-line change that sets `spec.replicas: 0` in
   `apps/cluster-diagnosis/manifests/deployment.yaml`, and wait until the pod is
   gone:

   ```sh
   kubectl -n monitoring wait --for=delete pod \
     -l app.kubernetes.io/name=cluster-diagnosis --timeout=180s
   ```

2. Run the reset against the same claim. The pod below mounts the ledger, which
   the reset needs: without the claim it would report success against its own
   empty scratch volume.

   ```sh
   IMAGE="$(kubectl -n monitoring get deployment cluster-diagnosis \
     -o jsonpath='{.spec.template.spec.containers[0].image}')"
   kubectl -n monitoring apply -f - <<YAML
   apiVersion: v1
   kind: Pod
   metadata:
     name: cluster-diagnosis-reset
     namespace: monitoring
   spec:
     restartPolicy: Never
     automountServiceAccountToken: false
     securityContext:
       runAsNonRoot: true
       runAsUser: 10001
       runAsGroup: 10001
       fsGroup: 10001
       seccompProfile:
         type: RuntimeDefault
     containers:
       - name: reset
         image: ${IMAGE}
         command: ["python3", "/app/diagnosis.py", "--reset-state"]
         env:
           - name: CLUSTER_DIAGNOSIS_STATE_ROOT
             value: /state
         securityContext:
           allowPrivilegeEscalation: false
           readOnlyRootFilesystem: true
           capabilities:
             drop: ["ALL"]
         volumeMounts:
           - name: state
             mountPath: /state
     volumes:
       - name: state
         persistentVolumeClaim:
           claimName: cluster-diagnosis-state
   YAML
   kubectl -n monitoring wait --for=jsonpath='{.status.phase}'=Succeeded \
     pod/cluster-diagnosis-reset --timeout=180s
   kubectl -n monitoring logs pod/cluster-diagnosis-reset
   kubectl -n monitoring delete pod cluster-diagnosis-reset
   ```

3. Merge the replicas back to `1` and confirm the loop is polling again.

`--reset-state` refuses to run while another process holds the lock, so step 1 is
a safety step, not a formality. The ledger's own count of the day is discarded by
the reset: that is what "grant a fresh day" means.

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

### What a message contains

Alertmanager has already sent the alert, the runbook link and the resolved
notice. The loop therefore speaks only when it knows something the alert does not
say, and the message is at most four short lines:

```text
FIRE KubePodNotReady [warning] immich/immich-server-6ddff46cbc-x4bb4 (immich-server) - firing 17m
last 15m: 40 sampled line(s) - network-timeout x32, unhealthy x32.
The liveness probe reportedly succeeds only because the API server is reachable,
so the readiness path is likely failing for a different reason. Check the Service endpoints.
```

- The first line is written by the loop: icon, state, severity, the alert the
  operator recognises, the object, and how long the alert has been firing.
- The second line is the new observation, written by the loop from the evidence
  pack: sampled lines with the signal names and counts, counted in lines that
  matched, never in events or restarts.
- The last lines are the only part the model writes: at most two sentences, 45
  words, plain text, no headings or Markdown. The loop rejects anything else
  rather than repairing it, and the model may answer `NO_UPDATE`, which sends the
  finding alone.
- Nothing about the pipeline is printed: no collection accounting, no classifier
  label, no provider error. Those stay in the metrics and the log.
- With no finding at all, the loop is silent: it does not call the model, spends
  nothing and sends nothing. The same finding is never sent twice.
- A close is only sent for an incident whose message reached the chat, and it
  says why it closed.

Delivery is separate from diagnosis: a narrative is queued in the outbox and
sent in the same iteration, a failure is retried on later polls without another
model call, the outbox holds at most 20 entries, and an entry older than six
hours is dropped and counted as expired. A closing message is only sent for an
incident the chat actually heard about, and it waits until that earlier message
has been delivered instead of overtaking it. Telegram can accept a message before the client gives up, so a
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
| `soyspray_diagnosis_outbox_pending`, `_outbox_oldest_seconds` | Delivery state |
| `soyspray_diagnosis_delivery_total`, `_outcome_total`, `_model_info` | Outcomes and serving model |
| `soyspray_diagnosis_last_success_timestamp_seconds` | Last message delivered, any outcome |
| `soyspray_diagnosis_last_diagnosis_timestamp_seconds` | Last successful provider answer |
| `soyspray_incident_open`, `_opened_timestamp_seconds` | Open incidents |
| `soyspray_incident_undiagnosed_timestamp_seconds` | Critical work with no answer yet |
| `soyspray_evidence_*`, `soyspray_classifier_*` | Evidence and classifier state |

Never-attempted work exposes no series, so the dashboard shows unknown rather
than a false zero. Six alerts cover the failure modes:
`SoysprayDiagnosisStale` (no metrics, or no completed poll for 15 minutes),
`SoysprayDiagnosisSourceUnreadable` (the loop polls but cannot read
Alertmanager, so nothing can be investigated), `SoysprayDiagnosisStateUnusable`,
`SoysprayDiagnosisProviderRejected`, `SoysprayDiagnosisUndiagnosed` (an open
critical incident with no answer for an hour) and
`SoysprayDiagnosisDeliveryStalled` (the oldest queued message has waited more
than thirty minutes).

## Models

`DEEPSEEK_PROFILE=flash` is the default: `deepseek-flash` with thinking
explicitly disabled, `max_tokens` 1200, a 60-second deadline. The ceiling is
1200 because a 512-token answer for a full incident payload came back
truncated, which the loop correctly refused to deliver. `reasoning` selects
`deepseek-v4-pro` with thinking enabled, `max_tokens` 4096 and a 90-second
deadline. `DEEPSEEK_MODEL` and `DEEPSEEK_THINKING` override either profile.

An empty or truncated answer is a failure, never a message: a reasoning model
that spends its whole budget before answering produces an explicit
`empty-content` outcome instead of an empty Telegram message. The model is asked
for an optional addition, not a report, so `NO_UPDATE`, an overlong answer, a
Markdown answer or an answer with a URL is rejected and the finding goes alone.
`soyspray_diagnosis_answer_total{result}` counts accepted, no-update and rejected
answers, and `soyspray_diagnosis_suppressed_total{reason}` counts the incidents
the loop examined and stayed silent about.

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
keeps only backup and restore evidence. The removed job was
`f2558fdf-209c-4dcc-a92b-9e5a3decf85f`; the retired ledger is kept beside the
laptop copy as `state.retired.json`.

Known-good revisions for a rollback:

| Step | Revision or digest |
| --- | --- |
| Running runtime image | `ghcr.io/kpoxo6op/cluster-diagnosis@sha256:3165dfe5…` (promotion commit `8d1a6398`) |
| Source merge that created the workload | `a7d6fb7b` |
| Last laptop runtime release | the commit shown by `readlink ~/.local/lib/soyspray-operations/previous` |

Roll back to the laptop loop:

1. Park the cluster loop first, or two loops will spend and notify
   independently: merge `spec.replicas: 0` for
   `monitoring/cluster-diagnosis` through the same Git path as the guarded
   reset, wait for the pod to be gone, and confirm no
   `apps/cluster-diagnosis/app/adapter.py` process is left on this laptop
   (`pgrep -af adapter.py`).
2. Restore the laptop loop: revert the commits that removed
   `apps/cluster-diagnosis/install.yml` and the runtime installer import, then
   run `ansible-playbook playbooks/operations/runtime/install.yml -e
   operations_revision=COMMIT -e diagnosis_enabled=true`. That restores the
   OpenClaw cron job and its dependencies: the job runs Codex through the
   OpenClaw CLI with the diagnosis profile under
   `~/.local/state/soyspray/cluster-diagnosis/profile`, so OpenClaw and the
   account behind that profile must still be usable.
3. Decide what happens to the day's spending. The two ledgers are separate
   schemas, so there is no tested conversion: either carry the cluster spend
   into the laptop ledger by hand (the fields are `budget[day].attempts` and
   `.tokens` in the cluster ledger, the equivalent counters in the laptop one)
   or accept a fresh laptop day deliberately. A pending outbox is dropped with
   the cluster ledger; nothing is delivered twice.

Roll back the provider only:

1. Revert the image digest to the last reviewed one.
2. `DEEPSEEK_PROFILE=reasoning` is a configuration change, not a rollback: it
   selects `deepseek-v4-pro` with thinking enabled and a larger ceiling. Use it
   to diagnose a provider problem, not to undo a release.
3. If the key must change, remove `monitoring/cluster-diagnosis-deepseek` and
   rerun the bootstrap with the new Vault value.
