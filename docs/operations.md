# Everyday operations

Start with the maintained repository commands. They read native Kubernetes and
Argo CD state and explain evidence gaps.

## Check the system

```sh
make apps
make status APP=boys FORMAT=json
make backup-status FORMAT=json
```

`make apps` lists applications and ownership. `make status` combines desired
source, live health, access, and recovery evidence for one application.
`make backup-status` reads native backup records and private restore reports.

## Read an incident

`make status APP=NAME` shows one application. The **Soyspray Operations**
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
2. Change the application folder and its technical README together.
3. Run the maintained application check and diff.
4. Open a pull request and wait for required checks.
5. Merge to `main`; Argo CD then follows the reviewed source.

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

## Detailed procedures

- [Native node removal and readd](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes):
  the retained-OS Kubespray path for one target at a time. The disruptive
  fallback requires separate authorization and can lose data.
- [Application operations](https://github.com/kpoxo6op/soyspray/tree/main/apps)
- [Ansible operations](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations)
- [Repository helper commands](https://github.com/kpoxo6op/soyspray/tree/main/scripts)
