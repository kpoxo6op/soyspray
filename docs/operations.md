# Everyday operations

Read native Kubernetes and Argo CD state; use the app README for checks.

## Check the system

```sh
kubectl -n argocd get applications
kubectl -n argocd get application boys -o yaml
kubectl -n longhorn-system get volumes.longhorn.io,backups.longhorn.io
kubectl get backups.postgresql.cnpg.io -A
```

Argo CD shows desired source, sync, health, and history. Longhorn and CNPG custom
resources and UIs show backup state. A schedule does not prove a completed
backup; private isolated restore reports remain beside the recovery procedure.
Prometheus keeps the native backup alerts without a laptop scrape target.

## Read an incident

The Argo CD UI shows each application. The **Soyspray Operations**
dashboard shows open incidents, source read status, evidence gaps and delivery
state. A missing series is unknown, not healthy.

Alertmanager sends critical and warning alerts directly to Telegram. The
cluster incident loop adds a short factual update only for a new observation or
supported correlation; it does not interpret logs with AI. The independent
`Watchdog` ping remains in place. A vanished alert is not verified recovery.

The loop runs as `monitoring/cluster-diagnosis`. Read its logs with
`kubectl -n monitoring logs deploy/cluster-diagnosis` and its metrics with
`kubectl -n monitoring exec deploy/cluster-diagnosis -- python3 /app/diagnosis.py
--print-metrics`. The maintained warning rules cover a stale loop, unreadable
Alertmanager source, unusable state and a stalled Telegram outbox.

## Change an application

1. Work on a branch.
2. Change the application folder and update its short README when needed.
3. Run the maintained application check and diff.
4. Open a pull request describing what changed, why, risk, and rollback. GitHub
   CI is the merge gate; affected local checks help during development.
5. Squash merge after CI passes and the change is verified safe. Argo CD follows
   `main`; confirm affected Applications are Synced and Healthy.

Do not use ad hoc Kubernetes writes for a lasting change. A live application
must not be retargeted to a topic branch.

For a dashboard or custom Prometheus alert rule, edit
[`apps/prometheus/config`](https://github.com/kpoxo6op/soyspray/tree/main/apps/prometheus/config).
After merge, `prometheus-config` updates a dashboard under its stable name or
removes a file deleted from Git. The stack and CRDs keep their separate
non-pruning owners. Verify `prometheus-config` is Synced and Healthy and check
the actual dashboard or rule; an alert disappearing is not proof of recovery.

Node-0, node-1 and node-2 use one native Kubespray procedure: prepare survivor
access and backups, remove, readd, then verify recovery. All validation drills
are complete. Keep disruption budgets and storage policy in place; the guide
covers first-member discovery and node-0's local storage without extra wrappers.

For voice recovery after a power interruption, check both the wake-word and
speech-recognition services. A healthy Home Assistant alone does not establish
that the device can hear commands. The
[voice guide](https://github.com/kpoxo6op/soyspray/tree/main/apps/voice-assistant)
includes transport checks and the spoken device test. The
[scoped storage operation](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/storage)
can release an unused multipath map blocking the existing speech model disk;
it preserves the PVC and refuses active maps.

## Detailed procedures

- [Native node removal and readd](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes):
  the retained-OS Kubespray path for one target at a time. The disruptive
  fallback requires separate authorization and can lose data.
- [Application operations](https://github.com/kpoxo6op/soyspray/tree/main/apps)
- [Ansible operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations)
- [Repository helper commands](https://github.com/kpoxo6op/soyspray/tree/main/scripts)
