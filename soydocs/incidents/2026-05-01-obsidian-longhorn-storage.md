# 2026-05-01 Obsidian LiveSync and Longhorn Storage Incident

## Plain-English Summary

Obsidian LiveSync failed with HTTP 503 because CouchDB lost its Kubernetes
endpoint. The endpoint disappeared because the CouchDB pod could not keep its
Longhorn volume mounted.

The deeper cause was storage under Longhorn. The node's `/storage` filesystem,
backed by the Samsung SSD used for Longhorn replica data, remounted read-only
after ext4 journal errors. Longhorn then entered repeated detach, attach,
salvage, and remount loops. The Obsidian volume was not the only affected
volume, but it was the user-visible one because the phone was actively syncing.

The immediate service recovery used the latest S3 CouchDB backup and a temporary
CouchDB rescue deployment backed by the node root disk instead of Longhorn.
This brought `https://obsidian.soyspray.vip` back online while preserving the
original Longhorn PVC for later forensic recovery.

The SSD is not proven completely dead: SMART still reports overall health
`PASSED`. It should still be treated as cooked for operational purposes. The
combination of `/storage` remounting read-only, `Current_Pending_Sector=14`,
`Reallocated_Event_Count=30`, and repeated Longhorn block-device I/O errors
means it is no longer safe storage for critical Longhorn volumes.

The affected node disk matches the AliExpress SSD order record supplied during
the incident:

- AliExpress order ID: `8199850113352085`
- Store: `Samsung Authorized Memory Store`
- Ordered: `2025-04-12`
- Item: `SAMSUNG SSD 870 EVO ... SATA3 2.5 inch`
- Selected capacity: `500GB`
- Node device: `/dev/sda`
- Node model: `Samsung SSD 870 EVO 500GB`
- Node serial: `S5Y4NFOR5613453`
- Mounted filesystem: `/storage` on `/dev/sda1`

The order page also showed order completion on `2025-04-25`, which means the
disk was roughly one year old at the time of this incident. Shipping address,
phone number, and payment details were intentionally not recorded here.

A replacement SSD was ordered from PB Tech during the incident so the failed or
suspect `/storage` disk can be retired instead of reused:

- PB Tech order number: `WO10167434`
- Ordered: `2026-05-01 18:48 NZST`
- Amount: `NZ$190.75`
- Estimated shipping date: `2026-05-04`
- Item selected during recovery: `PNY CS900 500GB 2.5" Internal SSD SATA`
- Shipping address was confirmed in the order but is intentionally not recorded
  here.

## User Impact

- Obsidian sync from phone/laptop failed with HTTP 503.
- CouchDB was briefly verified working after Longhorn recovered, then Longhorn
  I/O errors returned and made the original PVC unsafe to trust.
- The restored server state came from the latest successful offsite backup:
  `2026-05-01 00:55:03 UTC` (`2026-05-01 12:55:03 NZST`).
- Edits made after that backup may only exist on client devices until those
  devices sync back to the rescue CouchDB.

## Detection

- User reported Obsidian sync failing from phone while other services worked.
- `https://obsidian.soyspray.vip/` returned HTTP 503 from nginx.
- Kubernetes showed no endpoint for `obsidian-livesync-svc-couchdb`.
- Longhorn reported the Obsidian volume repeatedly attaching, detaching, and
  being auto-salvaged.
- Kernel logs showed ext4 and block I/O errors.

## Deadman / Watchdog Assessment

The Prometheus stack has a deadman's-switch route:

- Prometheus continuously fires `Watchdog`.
- Alertmanager routes `Watchdog` to `watchdog-healthchecks`.
- The receiver posts to Healthchecks.io:
  `https://hc-ping.com/ee92de78-bf59-4cb8-a41a-01382feb9a65`
- Healthchecks.io check name: `Soyspray`.
- Healthchecks.io description: `home cluster alert manager watchdog`.
- Notification methods were enabled for email `kpoxo6op-mail` and Telegram
  `kpoxo6op-telegram`.
- Actual Healthchecks.io schedule at review time:
  - Period: `1 day`
  - Grace time: `1 hour`

Assessment: the deadman did not fire for this incident because the
Healthchecks.io schedule was configured as a daily check, not a short watchdog.
With `1 day` period plus `1 hour` grace, Healthchecks would tolerate roughly 25
hours without pings before alerting. That is far too loose for a home-cluster
monitoring watchdog and explains why the Healthchecks page still showed `All
good` for May 2026.

Why:

- Alertmanager restarted at `2026-05-01 05:32:39 UTC`.
- Prometheus was not fully recovered until the new pod became ready at about
  `2026-05-01 05:50:25 UTC`.
- A later Prometheus range query for `ALERTS{alertname="Watchdog"}` only showed
  fresh samples from `2026-05-01 05:53:00 UTC` onward.
- Healthchecks.io event history showed regular OK pings every 5 minutes after
  recovery, for example:
  - `2026-05-01 18:58 NZST` through `2026-05-01 21:23 NZST`
  - HTTPS POST from `118.148.130.35`
  - request body size `2001` bytes
  - user agent `Alertmanager/0.28.1`
- The post-recovery pings prove the Alertmanager-to-Healthchecks webhook path
  works when Prometheus and Alertmanager are healthy.
- They do not indicate a missed incident because the check's schedule was too
  broad to consider a short outage late.

What this does and does not prove:

- It proves the live Watchdog route and webhook destination were configured.
- It proves Healthchecks received regular OK pings after recovery.
- It proves the Healthchecks schedule was not suitable for detecting this class
  of Prometheus/Alertmanager outage.
- It does not prove that Healthchecks failed. Healthchecks behaved consistently
  with its configured daily schedule.

Recommendation: change the Healthchecks.io schedule to a shorter watchdog
window:

- Period: `10 minutes`
- Grace time: `10 minutes`

This would alert after roughly 20 minutes without Watchdog pings. A more
aggressive `5 minutes` period plus `5 minutes` grace is possible, but it is more
likely to alert on brief network or restart noise. Start with `10m + 10m` and
tighten later if it is quiet.

## Timeline

All times are UTC unless noted.

### Before the Incident

- `2026-05-01 00:55:03` - Obsidian offsite backup job started.
- `2026-05-01 00:55:07` - Obsidian offsite backup completed successfully for
  database `obsidian-main`.
- Backup object later used for restore:
  `s3://obsidian-offsite-archive-au2/obsidian-livesync/20260501-005503/obsidian-main-20260501-005503.json`.

### Failure Window

- `2026-05-01 05:09-05:10` - nginx logs showed the phone still syncing
  successfully.
- `2026-05-01 05:11` - CouchDB began returning failures and then nginx returned
  HTTP 503 because the CouchDB service had no ready endpoint.
- `2026-05-01 05:10-05:16` - Longhorn repeatedly requested remounts and
  auto-salvaged the Obsidian volume.
- About `2026-05-01 05:15` (`17:15 NZST`) - kernel logs showed ext4 journal
  failure and `/storage` remounted read-only.
- SMART data on `/dev/sda` showed warning signs:
  - `Reallocated_Event_Count=30`
  - `Current_Pending_Sector=14`
  - SMART overall health still reported passed, which was misleading for this
    incident.

### Storage Repair Attempt

- kubelet and containerd were stopped to release Longhorn mounts.
- `/storage` was unmounted.
- `e2fsck -f -y /dev/sda1` repaired the filesystem journal and modified the
  filesystem.
- `/storage` was remounted read-write and a write test succeeded.
- containerd and kubelet were restarted, then the node was rebooted to clear
  stale Longhorn engine state.

### Longhorn Control Plane Recovery

- Longhorn manager initially crash-looped after reboot.
- Longhorn manager was failing while applying generated default settings from
  the `longhorn-default-setting` ConfigMap. It hit Kubernetes optimistic-lock
  conflicts for settings such as:
  - `fast-replica-rebuild-enabled`
  - `default-replica-count`
  - `concurrent-replica-rebuild-per-node-limit`
- Argo self-heal for the `longhorn` app was paused.
- The live `longhorn-default-setting` ConfigMap was blanked.
- Longhorn manager and CSI then recovered.
- Longhorn volumes mostly returned to `attached healthy`.

### Obsidian Recovery Attempt on Original Volume

- The Obsidian pod was recreated after CSI registration recovered.
- CouchDB briefly came back and `https://obsidian.soyspray.vip/_up` returned
  HTTP 200.
- New kernel errors then appeared on Longhorn block devices.
- The original Obsidian Longhorn volume returned to detach/salvage behavior.
- The original PVC was preserved and not deleted:
  - PVC: `database-storage-obsidian-livesync-couchdb-0`
  - Longhorn volume: `pvc-87a2e7b1-6011-4580-8dce-e9433a6f0900`

### Rescue Restore

- Argo self-heal for `obsidian-livesync` was paused.
- The original `obsidian-livesync-couchdb` StatefulSet was scaled to zero.
- A clean Longhorn rescue PVC was attempted.
- That rescue PVC failed during `mkfs.ext4` with `Input/output error`, proving
  that new Longhorn writes were still not trustworthy enough.
- A temporary hostPath rescue deployment was created instead, using root disk
  storage:
  `/var/lib/obsidian-rescue-couchdb-data`.
- CouchDB initially failed because the StatefulSet Erlang node name and seedlist
  did not fit a Deployment rescue pod.
- The rescue deployment was patched to use:
  - `ERL_FLAGS=" -name couchdb@127.0.0.1 "`
  - local seedlist `couchdb@127.0.0.1`
  - health probes against `/` instead of `/_up` while system DBs were being
    created.
- System databases were created:
  - `_users`
  - `_replicator`
  - `_global_changes`
- `obsidian-main` was restored from S3 using `_bulk_docs` with
  `new_edits=false`.
- The bulk restore completed with:
  - `import_errors=0`
  - `doc_count=14878`

### Monitoring Recovery

- Alertmanager restarted at `2026-05-01 05:32:39 UTC`.
- Prometheus had repeated storage/mount recovery and WAL replay delays.
- A final Prometheus pod was created at `2026-05-01 05:50:01 UTC`.
- Prometheus containers started at `2026-05-01 05:50:11 UTC`.
- Prometheus became ready at about `2026-05-01 05:50:25 UTC`.
- Prometheus target health later showed smartctl exporter, node exporter,
  Prometheus, Alertmanager, and operator targets all `up`.

## Root Cause

The root cause was unreliable storage under Longhorn:

- `/storage` remounted read-only after ext4 journal errors.
- Longhorn replicas live under `/storage`, so Longhorn could not safely manage
  volume metadata or replica data.
- After filesystem repair, Longhorn recovered enough for many volumes to come
  back, but new I/O errors on Longhorn devices showed the storage layer was
  still unsafe.
- Because this cluster uses a single node and Longhorn replica count of 1, a
  single storage device problem directly affects volume availability.

## Contributing Factors

- Longhorn had only one replica for these volumes, so there was no second good
  replica to fail over to.
- SMART "overall-health passed" did not mean the disk was safe; pending sectors
  and reallocation events were the relevant evidence.
- Longhorn manager startup was blocked by generated default-setting updates,
  adding a control-plane recovery problem on top of the data-path problem.
- Prometheus itself used Longhorn storage, so monitoring was degraded during the
  storage incident.
- Obsidian LiveSync depends on a single CouchDB PVC, so the user-visible sync
  path failed as soon as that PVC stopped mounting.
- Argo self-heal would have reverted temporary rescue changes unless it was
  paused.

## What Worked

- The latest Obsidian S3 backup existed and restored cleanly.
- The backup had a small enough dataset to restore quickly once CouchDB was
  reachable.
- Healthchecks/Watchdog design should have detected the monitoring outage even
  when Prometheus itself was unavailable.
- Pausing Argo apps prevented self-heal from fighting the live rescue.
- Keeping the original PVC detached preserved the possibility of later forensic
  recovery.
- The hostPath rescue on root disk isolated Obsidian from the unstable Longhorn
  storage path.

## What Did Not Work

- Longhorn replica count 1 provided no practical protection from a single disk
  or filesystem problem.
- Prometheus storage on Longhorn meant alert history and observability were
  impaired during the exact failure being investigated.
- The default Longhorn settings ConfigMap caused manager startup conflicts
  during recovery.
- The first clean rescue PVC was also on Longhorn and failed at filesystem
  creation, which cost time.
- The CouchDB chart's StatefulSet-specific Erlang naming/seedlist did not work
  unchanged for a rescue Deployment.

## Current Live State After Recovery

- `https://obsidian.soyspray.vip/_up` returns HTTP 200 with:
  `{"status":"ok","seeds":{}}`
- `obsidian-main` exists with `14878` documents.
- The live CouchDB pod is:
  `obsidian-livesync-couchdb-hostpath-rescue-6dddfb4bbf-4k9ft`
- The live data path is:
  `/var/lib/obsidian-rescue-couchdb-data`
- The original Longhorn Obsidian volume remains preserved and detached:
  `pvc-87a2e7b1-6011-4580-8dce-e9433a6f0900`
- Last known original Longhorn volume state after recovery was
  detached/unknown.
- The live Obsidian services and ingress still work because the rescue
  deployment uses the existing service selector labels:
  `app=couchdb,release=obsidian-livesync`.
- The following Argo apps were intentionally left paused:
  - `longhorn`
  - `obsidian-livesync`
- Draft PR opened for durable Longhorn config and incident notes:
  `https://github.com/kpoxo6op/soyspray/pull/132`

## What To Do Next

### Immediate

- Do not delete the original Obsidian PVC.
- Do not wipe the Obsidian vault on phone or laptop.
- Let the most up-to-date client sync to the restored server first.
- Change the Healthchecks.io `Soyspray` watchdog schedule for check
  `ee92de78-bf59-4cb8-a41a-01382feb9a65` from `1 day` period plus `1 hour`
  grace to `10 minutes` period plus `10 minutes` grace.
- Keep `obsidian-livesync` Argo self-heal paused until the rescue state is made
  declarative or migrated back to a stable PVC.

### Storage

- Treat the Samsung SSD backing `/storage` as failed/suspect, even though SMART
  overall health says `PASSED`.
- Replace or retire the disk before trusting Longhorn with critical data again.
- Replacement order placed with PB Tech: `WO10167434`, `NZ$190.75`, estimated
  shipping `2026-05-04`.
- Do not run new critical Longhorn volumes on this disk; a fresh rescue PVC
  already failed during `mkfs.ext4` with `Input/output error`.
- After disk replacement, run a full SMART long test and verify pending sectors
  do not remain.
- Add alerting for:
  - `Current_Pending_Sector > 0`
  - reallocated-event/reallocated-sector counter increases
  - kernel log evidence that `/storage` remounted read-only
  - Longhorn volume filesystem creation or mount I/O errors
- Consider moving Longhorn data to newer storage or adding a second node/disk so
  replica count 2+ is meaningful.

### Preventing Single-SSD Outages

Backups protected the data, but they did not prevent the outage. The outage
happened because the active storage path had one physical SSD as a hard failure
domain. To avoid this class of outage, the cluster needs active storage
redundancy, not only restoreable backups.

Recommended target state:

- Stop treating a single `/storage` SSD as reliable infrastructure for critical
  PVCs.
- Use at least two independent storage devices before moving critical workloads
  back onto Longhorn.
- Prefer one of these designs:
  - two Kubernetes nodes with Longhorn replicas on separate physical disks, or
  - one node with mirrored local storage for `/storage` using ZFS mirror,
    mdraid1, or another boring mirror layer before Longhorn writes to it.
- Keep Longhorn replica count at `1` only while there is one real storage
  failure domain. Replica count `2` on the same disk or same unsafe path gives a
  false sense of safety.
- For critical small databases such as Obsidian LiveSync, consider a simpler
  known-good storage class backed by mirrored local storage instead of putting
  the database directly on a fragile single-disk Longhorn path.
- Keep S3/offsite backups, but document them as recovery/RPO protection, not
  uptime protection.
- Increase Obsidian backup frequency if the service remains on single-node
  storage; hourly or every-few-hours backups are more appropriate than daily
  backups for actively edited notes.
- Run scheduled SMART long tests and alert on nonzero pending sectors,
  reallocation counter increases, UDMA CRC errors, and filesystem remounts to
  read-only.
- Keep a spare known-good SATA SSD on hand. Waiting for shipping during an
  incident extends the period where services are running in rescue mode.
- Maintain and test a hostPath rescue manifest for small stateful services so a
  future Longhorn failure can be bypassed quickly while preserving the original
  PVC for forensic recovery.

### Obsidian

- After the storage layer is stable, migrate the rescue CouchDB data off
  hostPath and back into a normal declarative workload.
- Prefer a controlled backup/restore migration rather than reattaching the
  suspect original Obsidian Longhorn volume directly.
- Before migrating back, verify that a new Longhorn test volume can be created,
  formatted, mounted, written to, deleted, and recreated without kernel I/O
  errors.
- Keep the S3 backup restore procedure documented and tested.
- Consider increasing Obsidian backup frequency while using a single-node
  storage setup, because the practical RPO was the last daily backup.
- Keep the temporary rescue manifest/runbook available so future recovery can
  go straight to an alternate storage path when Longhorn itself is suspect.

### Monitoring

- Keep the deadman check external to the cluster.
- Add a short runbook section explaining how to verify Healthchecks.io events.
- Keep the Healthchecks.io period/grace aligned with the Alertmanager Watchdog
  repeat cadence. Since Alertmanager sends Watchdog pings about every 5 minutes,
  a `10m` period and `10m` grace is a reasonable starting point.
- Consider moving Prometheus to either:
  - root disk/local path with backup, or
  - a more reliable storage class,
  so alert history is less likely to disappear during Longhorn incidents.
- Do not rely on Prometheus alone for disk death signals when Prometheus is on
  the same storage failure domain.
- Add an alert that treats nonzero pending sectors as actionable even when SMART
  overall health is still "passed".
- Add an explicit alert/runbook for `/storage` remounting read-only.

### Argo and Longhorn

- Merge and deploy PR #132 before re-enabling Longhorn app self-heal.
- Re-enable Argo self-heal only after live state matches repo state.
- Keep Longhorn runtime settings out of the Helm-generated
  `longhorn-default-setting` ConfigMap where possible. Use explicit Setting
  manifests only for settings that really need GitOps ownership.

## Next-Time Runbook

1. Confirm whether the failure is endpoint-level:
   `kubectl -n obsidian get pods,endpoints,pvc`.
2. Check Longhorn volume state:
   `kubectl -n longhorn-system get volumes.longhorn.io -o wide`.
3. Check node storage before restarting workloads:
   `mount | grep /storage`, `dmesg -T`, and SMART pending/reallocation
   counters.
4. If pending sectors, reallocation events, read-only remounts, or Longhorn
   medium/I/O errors are present, assume the disk/storage path is unsafe until
   proven otherwise.
5. Stop write-heavy workloads and preserve the original PVC/volume before
   experimenting with recovery.
6. If `/storage` is read-only, stop kubelet/containerd before filesystem
   repair to release Longhorn processes.
7. Repair `/storage` only after confirming the affected device.
8. Restart Longhorn and CSI, then verify a harmless new test volume can format
   and mount before trusting Longhorn for rescue workloads.
9. If new Longhorn writes fail, stop testing Longhorn-backed rescue PVCs and use
   root disk hostPath or another known-good storage path for Obsidian,
   restore from S3, and leave the original PVC untouched.
10. Pause Argo apps before live rescue changes, and record which apps were
   paused.
11. Verify externally:
   - `https://obsidian.soyspray.vip/_up`
   - authenticated `obsidian-main` document count
   - Prometheus target health
   - Healthchecks.io deadman event history
12. Let the most current phone/laptop vault sync back to the rescue CouchDB
   before deleting old server-side storage.
13. Write the repo-side fix and incident note before re-enabling Argo self-heal.

## Lessons Learned

- A single-node Longhorn setup with replica count 1 is not high availability; it
  is mostly a Kubernetes-friendly volume manager over one local failure domain.
- A single SSD under `/storage` is the outage boundary. If that SSD remounts
  read-only or starts returning I/O errors, every critical PVC depending on it
  can fail together.
- Backups are necessary but they solve recovery, not availability. Preventing
  this outage requires mirrored storage or a second node/disk failure domain.
- SMART overall health is too coarse for operations. Pending sectors and kernel
  I/O errors matter more.
- Monitoring must have an external deadman because cluster-local monitoring can
  fail with the cluster.
- A deadman only works if its external timeout matches the outage size we care
  about. A `1 day` Healthchecks period plus `1 hour` grace is effectively a
  daily heartbeat, not a Prometheus outage detector.
- Recovery should first protect data, then restore service, then make the live
  state declarative. Trying to make everything clean immediately can increase
  data-loss risk.
- For Obsidian, client devices are also part of recovery. After a server restore
  from backup, the safest next step is to let the most current client sync back
  before deleting any old server-side volume.
