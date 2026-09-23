# Cluster incident updates

Alertmanager sends critical and warning alerts directly to the private Telegram
chat. This loop groups related alerts and adds a short factual update only when
it finds a distinct observation. It does not call an AI provider or classifier.
No update means the direct alert already said what is known; it does not mean the
service is healthy.

```text
Alertmanager ──► direct Telegram alert
       └──────► incident loop ──► bounded Loki evidence ──► factual update, if new
Prometheus ──────────────────────► /metrics
```

## Normal use

```sh
make status APP=cluster-diagnosis FORMAT=json
make check APP=cluster-diagnosis
make diff APP=cluster-diagnosis
kubectl -n monitoring logs deploy/cluster-diagnosis --tail=50
kubectl -n monitoring exec deploy/cluster-diagnosis -- python3 /app/diagnosis.py --print-metrics
```

The loop polls Alertmanager every two minutes. It records critical and warning
incidents, groups alerts by application or node, and attaches application
symptoms to a node incident only when the current pod-to-node map supports that
relationship. It reads at most six Loki targets, 40 lines per target and 120
lines per incident. The pod has no Kubernetes service account token. Its
NetworkPolicy permits only monitoring reads, DNS and Telegram delivery.

A single alert or a synthetic acceptance check normally produces no second
message. A separate failure phrase in a structured warning/error log, or two
alerts naming one resource, may produce an update. Signal labels describe
**sampled log lines**, not counted failures or a proven root cause. Successful
checks, free-text lines, held-back messages and stale or unavailable evidence
do not establish a failure. Window count changes alone do not trigger an update.
Only Alertmanager's explicit resolution is described as resolved. A vanished or
suppressed alert is closed with recovery marked unverified.

The state claim `monitoring/cluster-diagnosis-state` holds incident identity,
message signatures and the Telegram delivery outbox. It is **not backed up** and
has no isolated restore claim. A missing state file is a normal first start; an
unreadable or incompatible file stops the loop, preserves the file for diagnosis
and makes `/healthz` unready. The writer holds an exclusive lock and writes
atomically. The Deployment uses `Recreate` to keep one writer.

Delivery retries from the outbox on later polls. The outbox is bounded to 20
messages and entries expire after six hours; a Telegram timeout may have
succeeded remotely, so an ambiguous retry can duplicate a message. Check the
chat before manually resending. Native Alertmanager alerts and the independent
Watchdog continue even when this loop cannot deliver an update.

## Checks and limits

`make check APP=cluster-diagnosis` runs the application tests, lint and manifest
render. `make full-check` is the repository gate. The image workflow tests the
packaged runtime and opens a separate digest promotion PR after the source PR
merges. A source-only merge does not change the running image.

Prometheus exposes source read, state usability, outbox age, delivery outcomes,
open incidents, evidence gaps and the last completed poll. The rules
`SoysprayDiagnosisStale`, `SoysprayDiagnosisSourceUnreadable`,
`SoysprayDiagnosisStateUnusable` and `SoysprayDiagnosisDeliveryStalled` warn when
the supplemental path fails. `make restore-check APP=cluster-diagnosis` reports
that no maintained isolated restore exists for this operational state. Losing
the claim may lose pending updates and deduplication history.

The Telegram bot token comes from the existing
`monitoring/alertmanager-telegram-secret`. Bootstrap checks that this shared
identity is readable; it does not create, change or delete it. No DeepSeek key
is mounted. The old dedicated provider Secret is retired only through the
reviewed `apps/cluster-diagnosis/retire-provider-secret.yml` operation after
the new image is live; the recovery Vault
file remains outside the cluster.

## Recovery and rollback

If the loop cannot read state, inspect the pod log, claim and volume first.
Preserve a copy of the state file before a reset. A reset discards incident and
outbox history and may cause repeat updates. Stop the writer through a Git
change to `spec.replicas: 0`, confirm the pod is gone, then run the reviewed operation against **the existing claim**:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become \
  --become-user=root --user ubuntu apps/cluster-diagnosis/reset-state.yml \
  -e state_reset_confirm=true
```

Restore `spec.replicas: 1` through Git and verify a fresh poll.
Do not run `--reset-state` against an empty scratch volume and mistake it for a
repair of the claim.

Rollback uses a reviewed revert of the source and digest promotion commits via
GitHub and Argo CD. Before restoring the old AI image, restore its dedicated
Secret from the existing private Vault through its former bootstrap revision.
Preserve the state claim and check the outbox and Telegram chat during rollback;
the older image may interpret retained incident records under its former
message rules. Reverting a digest is a deployment action, not proof of recovery.
