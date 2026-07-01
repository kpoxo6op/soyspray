# 2026-07-01 Longhorn SSD Expansion Report

## Short Version

The two worker SSDs were installed, formatted, mounted at `/storage`, added
back into Longhorn, and then the active Longhorn volumes were expanded from one
replica to three replicas.

Result: the active workload storage is now spread across all three nodes.

Final live check:

- Longhorn app in Argo CD: `Synced`, `Healthy`, last operation `Succeeded`.
- Active Longhorn workload volumes: `20` healthy volumes with `3` replicas.
- Old preserved volume: `1` unknown volume with `1` replica, left alone.
- Failed replicas: `0`.
- Longhorn disks: all three nodes are `Ready=True` and `Schedulable=True`.

## Before

Before the SSD install, only `node-0` had proper Longhorn storage.

```text
Before SSD install

node-0
  /storage -> real PNY SSD
  Longhorn replicas lived here

node-1
  /storage -> just a directory on root disk
  no real Longhorn data should live here

node-2
  /storage -> just a directory on root disk
  no real Longhorn data should live here
```

The cluster had three Kubernetes nodes, but storage was not really stretched.
The worker nodes were compute nodes only until the SSDs were installed.

## SSD Install

The new PNY 500GB SATA SSDs were installed in `node-1` and `node-2`.

They were prepared with:

```text
playbooks/operations/storage/prepare-longhorn-worker-ssd.yml
```

That playbook:

- checked the stable `/dev/disk/by-id/...` device paths
- refused non-PNY or non-500GB disks
- repartitioned and formatted the two worker SSDs
- mounted them at `/storage`
- added persistent `/etc/fstab` entries
- ran a write/sync/delete test on `/storage`

After that, the host layout became:

```text
After SSD install

node-0
  /storage -> PNY SSD

node-1
  /storage -> PNY SSD

node-2
  /storage -> PNY SSD
```

## Longhorn Disk Fix

Longhorn already had old worker disk entries for `/storage`.

Those old entries were created when `/storage` on `node-1` and `node-2` was
only a root-disk directory. After the real SSDs were mounted, Longhorn noticed
that the filesystem had changed.

Longhorn reported:

```text
DiskFilesystemChanged
```

That was expected.

There were zero Longhorn replicas on `node-1` or `node-2`, so the old empty disk
entries were safely:

```text
disable scheduling
remove stale disk entry
add disk entry back at /storage
wait for Ready/Schedulable
```

After reconciliation:

```text
Longhorn storage nodes

node-0 /storage  Ready  Schedulable
node-1 /storage  Ready  Schedulable
node-2 /storage  Ready  Schedulable
```

## Replica Expansion

Longhorn was then moved from one replica to three replicas for active workload
volumes.

Simple meaning:

```text
Before

Volume A
  replica 1 -> node-0

If node-0 storage died, the volume was in trouble.
```

```text
After

Volume A
  replica 1 -> node-0
  replica 2 -> node-1
  replica 3 -> node-2

Now each active volume has copies on all three SSD-backed nodes.
```

The live defaults were also changed so new default Longhorn volumes ask for
three replicas:

```text
default-replica-count = 3
StorageClass longhorn numberOfReplicas = 3
```

## Rebuild Watch

After changing the active volumes to three replicas, Longhorn had to copy data
to the new worker SSDs.

During this phase, volumes showed as `degraded`. That was normal while copies
were still being built.

The useful Longhorn engine states were:

```text
RW = good replica, read/write
WO = rebuilding replica, write-only while copying
```

The rebuild was watched until the final state was:

```text
engine_modes = RW:60
failed_replicas = 0
```

That means all 20 active volumes had all 3 replicas healthy:

```text
20 active volumes x 3 replicas = 60 healthy replicas
```

## Final Shape

Current storage shape:

```text
                 Longhorn active volumes
                         |
          +--------------+--------------+
          |              |              |
       replica        replica        replica
          |              |              |
       node-0         node-1         node-2
       /storage       /storage       /storage
       PNY SSD        PNY SSD        PNY SSD
```

Final disk schedule:

```text
node-0  457Gi max  303Gi scheduled  435Gi available  Ready  Schedulable
node-1  457Gi max  303Gi scheduled  435Gi available  Ready  Schedulable
node-2  457Gi max  303Gi scheduled  435Gi available  Ready  Schedulable
```

Final volume state:

```text
20 active volumes  -> healthy, 3 replicas
 1 old volume      -> unknown, 1 replica, intentionally left alone
 0 failed replicas
```

## What This Does And Does Not Mean

This does mean:

- active Longhorn workload storage is now spread across the three SSD nodes
- a single node/disk loss should not immediately destroy active Longhorn data
- new default Longhorn volumes should request three replicas
- Git now matches the Longhorn defaults after PR #156 was merged

This does not mean:

- backups are optional
- the cluster has a three-node control plane
- the old unknown preserved volume is fixed
- disk space is unlimited

The storage layer is healthier now, but backups and restore testing still
matter.

## Remaining Follow-Up

- Fix or split `smartctl-exporter` so SMART metrics cover the new worker SSDs.
- Decide separately what to do with the old unknown preserved Longhorn volume.
- Keep watching disk pressure because three replicas use about three times the
  storage of one replica.
