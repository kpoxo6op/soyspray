# Node recovery

These operations remove and rebuild node-2 without reinstalling its OS or
formatting either filesystem. Kubespray owns Kubernetes, etcd, the container
runtime, and CNI. Longhorn owns replica movement. Use the exact sequence below.

The destructive boundary is one host: `node-2` at `192.168.20.12`. Preserve
the root filesystem UUID `d3507a31-6115-4f40-affc-ca5164120e50` and the
`/storage` filesystem UUID `49c092f4-dd55-41f5-99c6-854f8b44af4e`.

## Prepare the controller

Use a clean checkout of the reviewed `main` revision. The recovery runtime is
enough; npm, frontend packages, and browser tools are not required:

```sh
git submodule update --init --recursive
python3 -m venv soyspray-venv
soyspray-venv/bin/pip install -r requirements-recovery.txt
soyspray-venv/bin/ansible-galaxy collection install -r requirements-ansible.yml -p collections --force
revision="$(git rev-parse HEAD)"
test "$revision" = "$(git rev-parse origin/main)"
test -z "$(git status --porcelain --untracked-files=no)"
```

Keep private evidence outside the checkout. Use one operation ID:

```sh
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)"
state="$HOME/.local/state/soyspray/node-recovery"
mkdir -p "$state/etcd" "$state/storage" "$state/preflight"
chmod 700 "$state" "$state/etcd" "$state/storage" "$state/preflight"
```

## Recovery gates

Run `make go` on the delivered revision. Complete the app E2E matrix and fresh
isolated Home Assistant and Immich restores. The Immich report must contain a
real disposable asset, `production_inputs: not read`, and completed cleanup.
Do not use a zero-asset report.

Capture and validate a fresh etcd snapshot on node-0:

```sh
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/nodes/snapshot-etcd.yml \
  -e etcd_snapshot_label="$run_id"
snapshot="$state/etcd/$run_id.db"
snapshot_status="$state/etcd/$run_id.status.json"
snapshot_sha256="$(sha256sum "$snapshot" | awk '{print $1}')"
```

Collect current backup evidence without printing recovery credentials:

```sh
backup_evidence="$state/preflight/$run_id-operations.jsonl"
soyspray-venv/bin/python -m scripts.operations_evidence \
  --once --output "$backup_evidence"
```

`preflight-node2-removal.yml` requires fresh Boys, Obsidian, Vaultwarden, and
Immich backup observations. It also requires three healthy etcd endpoints,
the protected snapshot checksum, current CloudNativePG recovery windows, and
the non-zero Immich restore report. Every active Longhorn volume must be
healthy. The only non-healthy exception is the exact detached retired
`jellyfin-config` volume, which must have no running replica or attachment.

## Evacuate Longhorn

First run `playbooks/operations/storage/protect-loki-before-node2.yml`. It must
report two healthy Loki replicas. Then inspect and apply the native evacuation:

```sh
runner="soyspray-venv/bin/python playbooks/operations/nodes/run-node2-rebuild.py"
$runner evacuate --revision "$revision" --run-id "$run_id"
$runner evacuate --apply --revision "$revision" --run-id "$run_id"

evacuation="$state/storage/$run_id.json"
```

The operation disables new target scheduling, records exact volume and replica
identities, temporarily uses two survivor replicas, requests native Longhorn
eviction, and waits for every recorded volume to be healthy on node-0 and
node-1. It never deletes a Replica object or a filesystem path.

The same command and run ID safely resume an interrupted evacuation. Before
native removal, rollback remains available:

```sh
$runner rollback-evacuation --apply \
  --revision "$revision" --evacuation "$evacuation"
```

This clears eviction, re-enables scheduling, and restores the recorded replica
policies on the original Kubernetes node identity. Do not use this rollback
after native removal.

## Remove node-2

The Authentik worker PDB must temporarily allow one disruption. Run the exact
wrapper. It repeats all current gates before importing Kubespray's native
`remove-node.yml` with graceful drain and narrow reset settings:

```sh
immich_report="$HOME/.local/state/soyspray/restores/immich/CHECK_ID/report.json"
$runner remove \
  --revision "$revision" --evacuation "$evacuation" \
  --snapshot "$snapshot" --snapshot-status "$snapshot_status" \
  --snapshot-sha256 "$snapshot_sha256" \
  --backup-evidence "$backup_evidence" --immich-report "$immich_report"

$runner remove --apply \
  --revision "$revision" --evacuation "$evacuation" \
  --snapshot "$snapshot" --snapshot-status "$snapshot_status" \
  --snapshot-sha256 "$snapshot_sha256" \
  --backup-evidence "$backup_evidence" --immich-report "$immich_report"
```

The runner accepts no Ansible passthrough flags. It pins `reset_nodes=true`, graceful removal,
`flush_iptables=false`, and `reset_restart_network=false`. It suppresses the
upstream prompt only because the wrapper checks the explicit authorization.
If drain, detach, etcd, storage, backup, or restore checks fail, node-2 remains
the recovery target and the reset must not be bypassed.

## Verify the retained-OS baseline

Inspect first, then remove only recorded Longhorn replica directories and
Kubernetes-owned network objects:

```sh
$runner clean --revision "$revision" --evacuation "$evacuation"
$runner clean --apply --revision "$revision" --evacuation "$evacuation"
```

The network helper removes only `KUBE-` and `cali-` chains, matching ipsets,
Calico/Kubernetes links, and CNI namespaces whose host peer is a Calico link.
It does not delete generic links or routes, flush a table, or restart host
networking. The playbook verifies SSH, both filesystem
UUIDs, inactive cluster services, absent cluster paths, and closed cluster
ports. It never formats, repartitions, or removes `/storage`.

## Rejoin and restore policies

All control-plane and etcd peers participate. The runner does not accept a
node-only limit, tags, skipped tags, or a start task:

```sh
$runner rejoin --revision "$revision" --evacuation "$evacuation"
$runner rejoin --apply --revision "$revision" --evacuation "$evacuation"
```

The dry-run validates the survivor cluster, retained host and filesystem,
storage preparation, inventory, and playbook syntax. Kubespray cannot reliably
simulate a fresh host because later tasks depend on binaries and systemd units
that earlier check-mode tasks only predict. The apply run prepares the existing
`/storage` filesystem without formatting, runs the full pinned Kubespray cluster
play, and requires a new Kubernetes node and etcd member ID in the original etcd
cluster.

Restore Longhorn scheduling and every recorded replica policy:

```sh
$runner restore --revision "$revision" --evacuation "$evacuation"
$runner restore --apply --revision "$revision" --evacuation "$evacuation"
```

Wait for healthy rebuilt replicas. Restore the Authentik worker PDB to
`minAvailable: 1` through a final Git PR. Then run `make go`, `make backup-status
FORMAT=json`, `make restore-check` for affected apps, and the complete E2E
matrix. Keep the etcd snapshot, evacuation plan, restore reports, and operation
times in private state. Remove only disposable test data and access.
