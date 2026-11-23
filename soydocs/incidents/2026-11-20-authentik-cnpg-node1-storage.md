# 2026-11-20 Authentik Outage after node-1 Storage Disruption

## Plain-English Summary

From 2026-11-20 to 2026-11-23, Authentik was down, so gi.soyspray.vip and the
other single sign-on apps could not log in. Nobody was paged for three days.

node-1 did not reboot. Its Longhorn storage was disrupted: every iSCSI session
on node-1 dropped, the node's Longhorn manager crashed, and its instance
manager was recreated. Every volume attached through node-1 lost its disk at
once. The databases failed over, but both Authentik standbys ended up on a
diverged timeline and could not rejoin.

Authentik's database required a synchronous standby for every commit
(`dataDurability: required`). With no standby, every write waited forever.
Waiting sessions filled all 100 connections, which also stopped the standbys
from connecting to repair themselves. Authentik's server crash-looped.

Prometheus was hit by the same event. multipathd grouped its fresh Longhorn
LUN into a stale map, so the pod could not mount its volume. With Prometheus
down, no rule ran. The Healthchecks.io dead-man check noticed, but its period
was one day, so the only notice came a day late and was missed.

## Timeline (UTC)

| Time | Event |
| --- | --- |
| 11-20 05:53 | node-1 kernel: all iSCSI sessions report `detected conn error (1022)` |
| 11-20 06:39 | Longhorn marks many node-1 replicas failed; CNPG fails over |
| 11-20 06:18 onward | Prometheus mount fails: `already mounted or mount point busy` |
| 11-20 06:53 | `longhorn-manager` on node-1 exits with code 2 |
| 11-20 06:57 | node-1 instance manager recreated; authentik-postgresql-1/2 never rejoin |
| 11-21 07:13 | Healthchecks.io "DOWN Soyspray" (1 day period + 1 h grace) |
| 11-23 08:00 | Investigation starts after Boris reports Authentik down |
| 11-23 08:01 | CNPG operator restarted: it had lost the barman plugin connection (`closed pool`) |
| 11-23 08:04 | Terminating blocked sessions lets standbys connect; `pg_rewind` fails (no common ancestor) |
| 11-23 08:56 | Logical dump taken earlier; guarded rebuild (#731) reclones both standbys |
| 11-23 09:00 | Authentik 3/3 healthy; login to gi.soyspray.vip verified end to end |
| 11-23 09:30 | Orphaned Longhorn replica removed; node-1 rebuild queue moves; immich-db-a-2 rebuilt |

## Root Causes

1. **Write availability depended on a standby.** `dataDurability: required`
   turned "no healthy standby" into "no writes", and the blocked sessions
   exhausted `max_connections`, which prevented self-repair.
2. **Diverged standbys had no supported repair path.** CNPG cannot `pg_rewind`
   across this divergence; a standby must be recloned, and the repository had
   no guarded operation for that.
3. **Longhorn LUNs were not excluded from multipath.** Longhorn reuses LUN
   WWIDs, so the earlier per-WWID exclusion could not work, and no node had it.
4. **One orphaned rebuild blocked node-1 storage recovery.** A replica that was
   running but absent from its engine's replica map held node-1's single
   rebuild slot for three days; 24 volumes stayed degraded.
5. **Monitoring had a single point of failure and a slow dead-man switch.**
   Prometheus was down, and the external check needed a day to notice.

The trigger for node-1's iSCSI drop and the manager crash is unknown; the
previous manager logs were gone when investigated.

## Fixes

| Change | Where |
| --- | --- |
| Guarded standby reclone, refusing primaries, healthy members, and stale backups | #731 `playbooks/operations/recovery/rebuild-cnpg-replica.yml` |
| `CNPGPrimaryWithoutStandby` (critical) and `CNPGStandbyNotStreaming` | #732 |
| Longhorn target (`IET`/`VIRTUAL-DISK`) excluded from multipath on all nodes | #734 `configure-longhorn-multipath.yml` |
| `dataDurability: preferred` for Authentik and Immich | #735 |
| `LonghornVolumeDegradedTooLong` and `LonghornVolumeFaulted` | #736 |
| Healthchecks.io watchdog period 1 day to 5 minutes, grace 10 minutes | Healthchecks.io (outside Git) |

## Lessons

- A storage disruption on one node must not take an app down. Durability
  settings that block writes need a matching page and a tested repair path.
- Monitoring must be watched from outside with a short period, and its own
  storage is part of the failure domain.
- Recovery queues can stall silently. Alert on degraded state that outlasts
  normal recovery time, not only on hard failure.
