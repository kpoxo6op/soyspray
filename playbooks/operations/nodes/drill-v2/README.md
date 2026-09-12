# Native node removal and readd

This guide records the native Kubespray path for a retained-OS node removal and
full readd. It is an operational exercise with a possible disruptive branch,
not a disk wipe, sudden power-loss test, node-0 test, or total-cluster
recovery. Keep private evidence outside Git. `record.sh` records commands and
their output without overwriting an existing log.

The tested scope was node-2 followed by node-1. Node-0 is excluded. The
observed run removed and readded both targets with new Kubernetes UIDs and
ended with three Ready, schedulable nodes, healthy three-member etcd, and 34
Healthy Argo CD Applications. It did not prove zero data loss or every write's
durability. An inactive Jellyfin-config volume remained an existing exception,
not a recovered-data claim.

Use the existing pinned Kubespray fork at `7fe8c51131046bba777bd78afee2509ebaaf8c6d`.
Its ownership patch protects the Argo-owned `cert-manager` namespace from
deletion. If that namespace is terminating, inspect and resolve that separate
incident before retrying; do not remove finalizers or admission registrations
as part of node recovery.

## Prepare

Use the ordinary repository Ansible environment, the full three-member
inventory, and root escalation. Do not use `--limit`, tags, `scale.yml`, or
check mode as a rebuild simulation. Preserve SSH, the OS, and mounted
filesystems.

```bash
git submodule update --init --recursive
source soyspray-venv/bin/activate
inventory="$PWD/kubespray/inventory/soycluster/hosts.yml"
ansible_cmd=(ansible-playbook -i "$inventory" --become --become-user=root --user ubuntu)
target=node-2  # use node-1 only after node-2 is recovered
test "$target" = node-1 || test "$target" = node-2
test "$target" != node-0
evidence="$HOME/.local/state/soyspray/node-drill-v2/$(date -u +%Y%m%dT%H%M%SZ)"
umask 077; mkdir -p "$evidence"
record() { bash playbooks/operations/nodes/drill-v2/record.sh "$evidence" "$@"; }
```

Before each target, use the existing `snapshot-etcd.yml`,
`make backup-status FORMAT=json`, and the existing application backup and
isolated restore commands by reference. Record the recovery point and limits.
Do not put credentials in command arguments or logs.

## Remove one target

Record a small target check, then call Kubespray directly. The fixed settings
are `reset_nodes=true`, `flush_iptables=false`, `reset_restart_network=false`,
`drain_retries=0`, and `allow_ungraceful_removal=false`. JSON extra-vars are
required because ambiguous string booleans caused two harmless pre-mutation
failures in the observed run.

For an interactive operator, omit `skip_confirmation` and answer Kubespray's
native confirmation prompt:

```bash
test "$target" = node-1 || test "$target" = node-2
record "$target-remove" "${ansible_cmd[@]}" kubespray/remove-node.yml \
  -e '{"node":"'"$target"'","reset_nodes":true,"flush_iptables":false,"reset_restart_network":false,"drain_retries":0,"allow_ungraceful_removal":false}'
```

For an explicitly authorized unattended run only, add
`"skip_confirmation":true` to the same JSON object. Do not add a limit or
weaken application PDBs or Longhorn policy.

## Authorized disruptive fallback

If the native drain stage fails, record the exact blocker first. Only then may
an authorized disruptive exercise use the native fallback once:

```bash
record "$target-remove-disruptive" "${ansible_cmd[@]}" kubespray/remove-node.yml \
  -e '{"node":"'"$target"'","reset_nodes":true,"flush_iptables":false,"reset_restart_network":false,"drain_retries":0,"allow_ungraceful_removal":true,"skip_confirmation":true}'
```

This can interrupt writes and lose data. A partial reset or etcd-member removal
failure requires inspection, not blind fallback. Never use this to bypass an
unclear quorum, survivor, disk, or readd failure.

## Readd and verify

Run the full pinned Kubespray reconciliation against the complete inventory:

```bash
record "$target-readd" "${ansible_cmd[@]}" kubespray/cluster.yml
```

Wait for native recovery. Compare the new Kubernetes UID with the saved UID.
Check three Ready/schedulable nodes, etcd health, preserved filesystems, active
Longhorn RW replicas, and application/data recovery. Distinguish a known
baseline exception from a new failure. Record observations before removal,
while removed, after readd, and after storage recovery. Use `record.sh` and a
short final handoff.

| Result | Action |
| --- | --- |
| Native removal and readd succeeds | Record recovery and continue only after the cluster is healthy. |
| Drain refuses on PDBs, attachments, or a last replica | Preserve the blocker; use the fallback only if already authorized. |
| Removal or readd is interrupted | Inspect membership, host state, and logs before retrying. |
| Longhorn rebuild progresses | Wait and record until required engines report RW. |
| Data is missing or corrupt | Preserve the original volume and use the existing app restore path; do not claim zero loss. |

The tested exercise retained the OS and filesystems. It did not test disk
formatting, node-0 removal, total-cluster recovery, or every production data
restore. Rollback for this documentation change is a Git revert; this guide
does not itself change live state.
