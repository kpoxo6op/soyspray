# Native node removal drill v2

Exercise node-2, recover the cluster, then repeat on node-1. Observe what
Kubespray, Kubernetes, and Longhorn do without the v1 evacuation and cleanup
sequence. This is an experimental, potentially destructive drill. Its first
two-node acceptance run is still pending.

`remove.yml` calls the pinned Kubespray `remove-node.yml`; `readd.yml` calls
its complete `cluster.yml`. The small shared check restricts the target and
requires a confirmation. It is not a cluster-health or backup validator.
`record.sh` only saves commands, output, UTC start/end times, and exit codes.

The default attempt drains normally. The explicit `lose NODE` scenario permits
native ungraceful removal after a recorded drain failure, including interruption
of writes and possible data loss. Obtain authorization for that scenario before
starting a run. Never infer it from a request for ordinary maintenance.

## Prepare once

Use the merged PR revision and the pinned submodule. Keep all three members in
the inventory: these are control-plane and etcd nodes, not worker-only nodes.
Node-0 remains the first member and is outside the removal scope. Full rejoin
reconciles all peers, so changes on the survivors are expected.

```bash
git submodule update --init --recursive
source soyspray-venv/bin/activate
inventory="$PWD/kubespray/inventory/soycluster/hosts.yml"
drill="$PWD/playbooks/operations/nodes/drill-v2"
ansible_cmd=(ansible-playbook -i "$inventory" --become --become-user=root --user ubuntu)
session="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)"
evidence="$HOME/.local/state/soyspray/node-drill-v2/$session"
umask 077
mkdir -p "$evidence"
record() { bash "$drill/record.sh" "$evidence" "$@"; }
record git git rev-parse HEAD
record kubespray-git git -C kubespray rev-parse HEAD
record backups make backup-status FORMAT=json
record backup-objects kubectl --request-timeout=15s -n longhorn-system get backups.longhorn.io -o json
```

Read the backup report, not just its exit code: zero means observations were
read, not that every application has a usable backup. Identify completed
pre-drill recovery points and the existing off-cluster credentials. Save the
Home Assistant volume identity and a named backup from `backup-objects.log`
for the independent restore below. Record gaps; an inaccessible or unusable
recovery path is an emergency decision, not a reason to invent a backup system
during this exercise. Do not expose credentials in command arguments or logs.

Use the preparation PR's passing full gate. Rerun affected checks only after
relevant source changes. Scheduled restore evidence does not expire because an
unrelated commit merged. No full application E2E matrix or fresh per-app restore
is required before each node removal. Actual restore exercises occur below.

## Observe at each phase

Call this with a unique name before removal, after removal, after readd, and
after recovery. A failed observation is evidence; inspect its log and continue
collecting the remaining observations. Never reuse a step name.

```bash
observe() {
  local phase=$1
  record "$phase-nodes" kubectl --request-timeout=15s get nodes -o json || true
  record "$phase-pods" kubectl --request-timeout=15s get pods -A -o wide || true
  record "$phase-apps" kubectl --request-timeout=15s -n argocd get applications -o json || true
  record "$phase-pv" kubectl --request-timeout=15s get pv -o json || true
  record "$phase-pvc" kubectl --request-timeout=15s get pvc -A -o json || true
  record "$phase-volumes" kubectl --request-timeout=15s -n longhorn-system get volumes.longhorn.io -o json || true
  record "$phase-engines" kubectl --request-timeout=15s -n longhorn-system get engines.longhorn.io -o json || true
  record "$phase-events" kubectl --request-timeout=15s get events -A --sort-by=.metadata.creationTimestamp || true
}
```

Save expected application URLs and a small read-only data sample or hash for
each affected stateful app in `notes.md`. This makes missing data distinguishable
from an application that merely becomes Healthy. Do not start a new test suite.
Use existing smoke commands where available and record their coverage limits.

## Run one target

Set `target=node-2` for the first pass. Set `target=node-1` only after completing
the first pass: three Ready/schedulable nodes, three healthy etcd members, no
ongoing storage recovery, and affected services usable. Classify any permanent
data loss explicitly before proceeding; do not continue through an active incident.

```bash
target=node-2
observe "$target-before"
record "$target-fs-before" ssh -o BatchMode=yes -o ConnectTimeout=10 "ubuntu@$target" \
  'findmnt -J -o TARGET,SOURCE,FSTYPE,UUID --target / && findmnt -J -o TARGET,SOURCE,FSTYPE,UUID --target /storage'
snapshot_label="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)"
record "$target-snapshot" "${ansible_cmd[@]}" playbooks/operations/nodes/snapshot-etcd.yml \
  -e "etcd_snapshot_label=$snapshot_label" \
  -e "etcd_snapshot_controller_dir=$evidence/$target-etcd"
record "$target-remove" "${ansible_cmd[@]}" "$drill/remove.yml" \
  -e "drill_node=$target" -e "drill_confirm=remove $target"
```

Stop at any failed command and select the matching scenario below. The snapshot
operation also checks current etcd health. It has no ten-minute evidence expiry.
Normal removal has one drain attempt using upstream timeouts. Do not loop it
unchanged, lower replica counts, move Loki, or relax PDBs before observing it.

After successful removal, save evidence that the target Node and etcd member
are absent. Observe for five minutes with one intermediate sample, recording
service failures and controller progress. This is planned removal, not a sudden
power-loss test; label an ungraceful fallback separately. Then readd:

```bash
observe "$target-removed"
record "$target-etcd-removed" ssh -o BatchMode=yes -o ConnectTimeout=10 ubuntu@node-0 \
  'sudo /usr/local/bin/etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/ssl/etcd/ssl/ca.pem --cert=/etc/ssl/etcd/ssl/admin-node-0.pem --key=/etc/ssl/etcd/ssl/admin-node-0-key.pem member list -w json'
record "$target-readd" "${ansible_cmd[@]}" "$drill/readd.yml" \
  -e "drill_node=$target" -e "drill_confirm=readd $target"
observe "$target-readded"
record "$target-fs-after" ssh -o BatchMode=yes -o ConnectTimeout=10 "ubuntu@$target" \
  'findmnt -J -o TARGET,SOURCE,FSTYPE,UUID --target / && findmnt -J -o TARGET,SOURCE,FSTYPE,UUID --target /storage'
record "$target-etcd-health" ssh -o BatchMode=yes -o ConnectTimeout=10 ubuntu@node-0 \
  'sudo /usr/local/bin/etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/ssl/etcd/ssl/ca.pem --cert=/etc/ssl/etcd/ssl/admin-node-0.pem --key=/etc/ssl/etcd/ssl/admin-node-0-key.pem endpoint health --cluster'
```

Use the complete inventory without `--limit`, tags, or `scale.yml`. Do not run
v1's empty-host cleanup or storage preparation by habit. The retained OS and
mounted filesystems are inputs to this drill. If a specific residual object or
missing prerequisite prevents rejoin, capture it and address only that defect.

After readd, compare the new Node UID with the saved UID; confirm the filesystems
and membership, actual application access/data, normal scheduling, and native
replica recovery. Longhorn engine `replicaModeMap` must show the required
replicas in `RW`, not just a running replica process. Allow temporary degradation
during the drill. Do not repeatedly change code while a rebuild is progressing.
Sample every two minutes while diagnosing, backing off to five minutes during
steady reconstruction. Save a final `observe "$target-recovered"` sample.

## Scenarios

| Observation | Next step |
| --- | --- |
| Graceful removal/readd succeeds | Record the native result and recovery time. Continue with the next target after recovery. No repair PR. |
| Drain fails on a PDB, attachment, or last-replica policy | Save the exact blocker and current volume state. If the authorized disruptive scenario is in scope, use the command below once. It skips drain failure and the detach wait; writes/data can be lost. No temporary PDB PR pair. |
| Native remove has already removed the etcd member or reset the host, then fails | Record the partial result and inspect membership. Do not apply the drain-failure fallback blindly. Consult Astra if the safe continuation is unclear. |
| Readd fails on a transient download or clearly identified retryable dependency | Capture the first error, correct only that dependency, retry the full same playbook once with a new log name. No blanket resets or cleanup. |
| Longhorn is degraded but rebuild progress continues | Wait and record. If it stops progressing across several samples, collect the affected volume/engine events; diagnose that volume only. |
| Service restarts but data is missing, corrupt, or cannot mount | Keep the original volume and logs. Rejoin/restore cluster infrastructure first; restore the affected app from its saved backup. Consult Astra for a production cutover or uncertain data identity. |
| API/quorum lost, survivor affected, disks ambiguous, or native rejoin remains stuck | Stop further removal. Send Astra one compact incident packet; prioritize recovery. Node-1 waits. |

Explicit disruptive fallback, only after a confirmed drain-stage failure:

```bash
record "$target-remove-disruptive" "${ansible_cmd[@]}" "$drill/remove.yml" \
  -e "drill_node=$target" -e drill_disrupt=true -e "drill_confirm=lose $target"
```

This remains a Kubespray reset, not a disk wipe. Risk acceptance is not a request
to delete backups, format drives, reset survivors, or erase unrelated app data.
Do not change Longhorn's cluster-wide drain policy for this exercise.

## Prove backup recovery and finish

If the drills cause loss, recover those applications as soon as infrastructure
allows it; do not wait until both drills finish. Existing isolated restores are
verification tools, not automatic production cutover tools. An emergency
cutover needs a scoped, reviewed Ansible operation with the original data kept
for analysis. Use Astra when that operation does not already exist.

After the two passes, restore Home Assistant from the **saved pre-drill** volume
and named backup, independently of its current production PVC. Also run the
existing paired Immich restore once to check the database-plus-files path:

```bash
# Set these from the pre-drill record, not the current production claim.
record restore-saved-home-assistant python -m scripts.restore_durable \
  --app home-assistant-config --source-volume "$saved_ha_volume" --backup "$saved_ha_backup"
record restore-immich env SOYSPRAY_RECOVERY_KUBECONFIG="$HOME/.kube/config" \
  SOYSPRAY_RECOVERY_INVENTORY="$inventory" make restore-check APP=immich
record final-backups make backup-status FORMAT=json
```

Keep the restore report paths, selected recovery points, actual data checks, and
cleanup results. A zero-asset Immich restore cannot prove photo recovery. Record
that gap instead of adding personal data or claiming success. Do not repeat a
passing equivalent restore already performed during incident recovery. These
checks prove these recovery paths, not every app or total-cluster reconstruction.

Write `handoff.md`: per-target before/after Node UID, native commands and result,
removal/rejoin/rebuild durations, outages/data loss, automatic versus assisted
recovery, restore proof, exact fixes/commits, unresolved gaps, and candidates for
deletion from v1. A `START` without `END` means an interrupted command: inspect
the process and live state before a retry. The recorder does not supervise it.

Do not run a broad refactor during the exercise. Keep incidental improvements
in the handoff. Preserve the v1 files until v2 acceptance and a separate cleanup
review; do not combine the two procedures. Reverting this PR removes the v2
entry points but cannot undo a completed removal or recover data.

## Checks and references

`make go` runs the repository gate, including offline execution tests with fake
native playbooks. Locally, syntax-check both entry points with the pinned
submodule. No local test executes a real node operation. Native Ansible check
mode is not a reliable fresh-node simulation and is deliberately rejected.

- [Kubespray node operations](https://github.com/kubernetes-sigs/kubespray/blob/master/docs/operations/nodes.md)
- [Longhorn native replica eviction](https://longhorn.io/docs/1.12.1/nodes-and-volumes/nodes/disks-or-nodes-eviction/)
- [Existing application recovery](../../recovery/README.md)
