# Node removal and readd

Use native Kubespray for node-0, node-1 or node-2, one at a time. All drills
are complete; no repeat is required. This procedure retains the OS and
filesystems. Disk replacement and total-cluster recovery are outside its scope.

## 1. Prepare

Use merged `main`, its pinned Kubespray ownership protections and the complete
three-node inventory. No node-only limits, tags, `scale.yml` or check-mode drill.

- Start with three Ready/schedulable nodes and healthy etcd. Save the target UID,
  filesystem identities, application/storage state and known exceptions.
- If the target is first in `kube_control_plane` or `etcd`, move it last in the
  inventory groups, with a healthy survivor first. Merge the fork change and
  Soyspray pin, verify the resolved order, then run full `cluster.yml` while
  all nodes are present. Keep the new order.
- **Before removal**, use a private kubeconfig pointing to a healthy survivor
  with CA verification. Check API access and `kube-public/cluster-info`.
  Correct a discovery endpoint that names the target; preserve the CA and other
  fields. Stale discovery blocked the node-0 readd.
- Identify completed backups, accessible off-cluster credentials and existing
  restore evidence. Repeat a restore only for recovery or a relevant gap.

For node-0, preserve `/`, `/storage` and `/srv/media` UUIDs, local PV/PVC bindings,
Zigbee identity and GPU access. Allow local workloads to be unavailable until
it returns. No formatting, storage initialization or media migration.
[Node-local backups](../../../apps/node-backup/README.md) cover selected Jellyfin
data and books; large media trees are excluded.

From the repository root:

```bash
set -euo pipefail
git submodule update --init --recursive
source soyspray-venv/bin/activate
target=node-0  # select the one authorized target
case "$target" in node-0|node-1|node-2) ;; *) exit 2 ;; esac
inventory="$PWD/kubespray/inventory/soycluster/hosts.yml"
ansible_cmd=(ansible-playbook -i "$inventory" --become --become-user=root --user ubuntu)
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

Verify the laptop snapshot copy before removing node-0, where it was created.
Read the backup report; exit zero is not backup proof. Keep credentials private.

## 2. Remove, then readd

Attempt normal drain once, with Kubespray's interactive confirmation:

```bash
remove_args='{"node":"'"$target"'","reset_nodes":true,"flush_iptables":false,"reset_restart_network":false,"drain_retries":0,"allow_ungraceful_removal":false}'
"${ansible_cmd[@]}" kubespray/remove-node.yml -e "$remove_args"
```

For an authorized unattended operation, use this command instead:

```bash
record "$target-remove" "${ansible_cmd[@]}" kubespray/remove-node.yml \
  -e "$remove_args" -e '{"skip_confirmation":true}'
```

If drain fails, record the blocker and keep PDBs/storage policy unchanged.
Only an explicitly authorized disruptive operation may use this fallback:

```bash
record "$target-remove-disruptive" "${ansible_cmd[@]}" kubespray/remove-node.yml \
  -e "$remove_args" -e '{"allow_ungraceful_removal":true,"skip_confirmation":true}'
```

Inspect partial reset/etcd changes before continuing. Past drill approval does
not authorize future disruption. Confirm the target Node and etcd member are
absent, then run full reconciliation:

```bash
record "$target-readd" "${ansible_cmd[@]}" kubespray/cluster.yml
```

## 3. Recover and finish

Wait while native recovery progresses. Verify the new Node UID, three
Ready/schedulable nodes, healthy three-member etcd, active Longhorn RW replicas
and usable applications with expected data. Verify actual filesystem mounts;
an empty directory on the root disk is not a restored media mount.

| Observation | Action |
| --- | --- |
| Interrupted removal/readd | Inspect membership, host state and logs; continue the identified native operation. |
| Longhorn rebuild is progressing | Wait. Do not add evacuation or replica-policy steps. |
| Ignored Calico cleanup warning | Check the actual readd result; do not add cleanup for the warning alone. |
| Persistent CSI/mount or multipath blocker | Identify the affected volume, LUN and users before a scoped repair. Preserve PVCs; do not flush maps or force-delete pods as a routine step. |
| Dependent workload failed during the outage | Restore its upstream first, then retry only the affected workload. |
| Missing or corrupt data | Preserve the original volume and use the affected app's existing restore procedure. |

For node-0, check Jellyfin data/GPU, the same Zigbee coordinator without
re-pairing, and Home Assistant/GI configuration. Physical playback/actuation,
zero write loss and full-media backup recovery remain unproven by these drills.

Finish recovery before another member's maintenance. Keep one private handoff
with revisions, identities, failures, assistance and restore results. Use
[existing app recovery](../recovery/README.md); no new runner or drill is needed.
