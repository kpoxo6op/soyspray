# Node operations

Use native Kubespray to remove and readd node-1 or node-2, one at a time.
The validation drills are complete. Use this procedure for requested
maintenance; no repeat drill is required. It retains the OS, SSH and mounted
filesystems. Node-0 removal, disk replacement and total-cluster recovery are
outside this procedure.

Use the merged repository revision and its pinned Kubespray submodule. The
fork's cert-manager ownership protection must remain: Kubespray must not
delete the Argo-owned namespace. Keep all three nodes in the inventory.
Full readd reconciles the surviving peers too; do not use `--limit`, tags,
`scale.yml` or check mode as a rebuild simulation.

## Prepare one target

From the repository root, select the target and a private log directory:

```bash
set -euo pipefail
git submodule update --init --recursive
source soyspray-venv/bin/activate
inventory="$PWD/kubespray/inventory/soycluster/hosts.yml"
ansible_cmd=(ansible-playbook -i "$inventory" --become --become-user=root --user ubuntu)
target=node-2  # select node-1 or node-2
case "$target" in node-1|node-2) ;; *) exit 2 ;; esac
session="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)"
evidence="$HOME/.local/state/soyspray/node-operations/$session"
umask 077
mkdir -p "$evidence"
record() { bash playbooks/operations/nodes/record.sh "$evidence" "$@"; }
record revision git rev-parse HEAD
record kubespray-revision git -C kubespray rev-parse HEAD
record backups make backup-status FORMAT=json
record etcd-snapshot "${ansible_cmd[@]}" playbooks/operations/nodes/snapshot-etcd.yml \
  -e "etcd_snapshot_label=$session" -e "etcd_snapshot_controller_dir=$evidence/etcd"
```

Read the backup report: a zero exit code does not mean every backup is usable.
Identify completed recovery points and off-cluster credentials. Use existing
restore evidence and [application recovery procedures](../recovery/README.md);
repeat a restore when needed for recovery or a relevant evidence gap, not for
each node or unrelated commit. Keep credentials out of command logs.

Save the target Node UID, filesystem identities, node/etcd membership,
application health and active storage state. Record known exceptions before
removal. Start with three Ready/schedulable nodes and healthy etcd; resolve an
active recovery before taking another member out.

## Remove

Use JSON extra-vars so booleans and values remain correctly typed. Do not use
the removed custom confirmation protocol. For an interactive operator, run
directly so Kubespray's native confirmation prompt stays visible:

```bash
remove_args='{"node":"'"$target"'","reset_nodes":true,"flush_iptables":false,"reset_restart_network":false,"drain_retries":0,"allow_ungraceful_removal":false}'
"${ansible_cmd[@]}" kubespray/remove-node.yml -e "$remove_args"
```

For an explicitly authorized unattended operation, use this command instead:

```bash
record "$target-remove" "${ansible_cmd[@]}" kubespray/remove-node.yml \
  -e "$remove_args" -e '{"skip_confirmation":true}'
```

Normal drain can refuse eviction because of PDBs or storage policy. Preserve
the failure and inspect the current state. Keep those policies in place.
If disruption and possible data loss are authorized for this operation, the
native fallback is available after a confirmed drain-stage failure:

```bash
record "$target-remove-disruptive" "${ansible_cmd[@]}" kubespray/remove-node.yml \
  -e "$remove_args" -e '{"allow_ungraceful_removal":true,"skip_confirmation":true}'
```

The fallback can interrupt writes and lose data. A partial reset or etcd-member
removal failure requires inspection before continuation. Past drill approval
does not authorize disruption during future maintenance.

## Readd and finish

Record that the target Node and etcd member are absent, then run the full
reconciliation:

```bash
record "$target-readd" "${ansible_cmd[@]}" kubespray/cluster.yml
```

Allow native recovery to progress. Verify a new Node UID, retained filesystems,
three Ready/schedulable nodes, healthy three-member etcd, active Longhorn
replicas in RW, and usable applications with the expected data. Health alone
does not prove write durability. Exclude known inactive volumes from recovery
claims. Finish recovery before any other member's maintenance.

| Observation | Response |
| --- | --- |
| Removal/readd was interrupted | Inspect membership, host state and logs; continue the native operation only after identifying the partial state. |
| Longhorn rebuild progresses | Wait. Do not adjust replica policy or add evacuation/cleanup steps. |
| Ignored Calico sandbox warnings during reset | Check the actual readd result; warnings alone do not require extra cleanup. |
| Persistent CSI mount-busy pod after storage recovery | Identify the affected pod and existing PVC; a scoped workload restart may be needed. Preserve the PVC and record assisted recovery. |
| A dependent service failed while its upstream was unavailable | Restore the upstream first, then retry only the affected workload. |
| Missing or corrupt data | Preserve the original volume and use the affected app's existing restore path. Record the recovery point and limits. |

Keep a short private handoff with revisions, before/after identities, failures,
interventions and recovery results. `record.sh` retains output, times and exit
codes and refuses reused step names. Inspect a failed command's log before a
retry; a journal START without END needs a process/state check first.

Other maintained operations include [etcd snapshots](snapshot-etcd.yml),
[disposable monitoring policy](../storage/README.md) and
[application recovery](../recovery/README.md).
