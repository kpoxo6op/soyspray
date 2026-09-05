"""Read backup coverage and recovery-point age from native Kubernetes records."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from scripts.app_status import display, observed, unknown

RESOURCES = {
    "applications": ("applications.argoproj.io", "argocd"),
    "claims": ("persistentvolumeclaims", None),
    "pvs": ("persistentvolumes", None),
    "volumes": ("volumes.longhorn.io", "longhorn-system"),
    "longhorn_backups": ("backups.longhorn.io", "longhorn-system"),
    "longhorn_jobs": ("recurringjobs.longhorn.io", "longhorn-system"),
    "targets": ("backuptargets.longhorn.io", "longhorn-system"),
    "clusters": ("clusters.postgresql.cnpg.io", None),
    "cnpg_backups": ("backups.postgresql.cnpg.io", None),
    "cnpg_schedules": ("scheduledbackups.postgresql.cnpg.io", None),
}


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def age(value, now):
    parsed = timestamp(value)
    if parsed is None:
        return unknown("The backup system has no valid timestamp with a timezone.")
    seconds = (now - parsed).total_seconds()
    if seconds < 0:
        return unknown("The backup timestamp is in the future; check the clocks.")
    return {"value": int(seconds)}


def identity(item):
    meta = item["metadata"]
    return meta.get("namespace", ""), meta["name"]


def backup_volume(item):
    state = item.get("status", {})
    labels = item["metadata"].get("labels", {})
    return (
        state.get("volumeName") or labels.get("backup-volume"),
        state.get("backupTargetName") or labels.get("backup-target"),
    )


def has_backup_error(state):
    return bool(state.get("error")) or any(
        key.lower() == "error" and value for key, value in (state.get("messages") or {}).items()
    )


def cluster_ref(item):
    return item["metadata"].get("namespace"), item["spec"].get("cluster", {}).get("name")


def items(data, key):
    value = data.get(key)
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        return value["items"]
    raise ValueError(f"{key}: {display(value) if value else 'No observation was supplied.'}")


def longhorn_report(data, now):
    claims = [
        x
        for x in items(data, "claims")
        if x.get("status", {}).get("phase") == "Bound"
        and not x["metadata"].get("deletionTimestamp")
    ]
    volumes = {x["metadata"]["name"]: x for x in items(data, "volumes")}
    pvs = {x["metadata"]["name"]: x for x in items(data, "pvs")}
    backups = items(data, "longhorn_backups")
    jobs = items(data, "longhorn_jobs")
    targets = {x["metadata"]["name"]: x for x in items(data, "targets")}
    rows = []
    for claim in sorted(claims, key=identity):
        name = "/".join(identity(claim))
        pv_object = pvs.get(claim["spec"].get("volumeName"), {})
        pv = pv_object.get("spec", {})
        csi = pv.get("csi", {})
        verified_binding = (
            csi.get("driver") == "driver.longhorn.io"
            and claim["metadata"].get("uid")
            and pv.get("claimRef", {}).get("uid") == claim["metadata"]["uid"]
        )
        volume = volumes.get(csi.get("volumeHandle")) if verified_binding else None
        if volume is None:
            rows.append(
                {
                    "claim": name,
                    "backup": unknown(
                        "No Longhorn volume binding was verified from the PVC UID and PV CSI handle."
                    ),
                }
            )
            continue
        volume_name = volume["metadata"]["name"]
        target_name = volume["spec"].get("backupTargetName")
        target = targets.get(target_name, {}).get("status", {})
        labels = volume["metadata"].get("labels", {})
        groups = [
            key.split("/", 1)[1]
            for key, value in labels.items()
            if key.startswith("recurring-job-group.longhorn.io/") and value == "enabled"
        ]
        schedules = [
            {
                "name": job["metadata"]["name"],
                "cron": job["spec"].get("cron"),
                "retain": job["spec"].get("retain"),
                "task": job["spec"]["task"],
            }
            for job in jobs
            if job["spec"].get("task") in {"backup", "backup-force-create"}
            and (
                set(groups).intersection(job["spec"].get("groups", []))
                or labels.get("recurring-job.longhorn.io/" + job["metadata"]["name"]) == "enabled"
            )
        ]
        matching = [
            backup for backup in backups if backup_volume(backup) == (volume_name, target_name)
        ]
        successful = [
            backup
            for backup in matching
            if backup.get("status", {}).get("state") == "Completed"
            and backup["status"].get("progress") == 100
            and not has_backup_error(backup["status"])
            and timestamp(backup["status"].get("snapshotCreatedAt")) is not None
        ]
        latest = max(
            successful, key=lambda b: timestamp(b["status"]["snapshotCreatedAt"]), default=None
        )
        failures = [
            b["metadata"]["name"]
            for b in matching
            if b.get("status", {}).get("state") in {"Error", "Failed"}
            or has_backup_error(b.get("status", {}))
        ]
        row = {
            "claim": name,
            "claim_uid": claim["metadata"].get("uid"),
            "pv_uid": pv_object.get("metadata", {}).get("uid"),
            "volume": volume_name,
            "groups": groups,
            "backup_schedules": schedules,
            "target": observed(target_name, "The volume has no backup target."),
            "target_available": observed(
                target.get("available"), "Longhorn has not reported target availability."
            ),
            "target_observed_at": observed(
                target.get("lastSyncedAt"), "The target has not been synced."
            ),
            "replicas": observed(
                volume["spec"].get("numberOfReplicas"), "Replica count is missing."
            ),
            "volume_health": observed(
                volume.get("status", {}).get("robustness"), "Volume health is missing."
            ),
            "failed_backups": failures,
            "unfinished_backups": [
                b["metadata"]["name"]
                for b in matching
                if b.get("status", {}).get("state") not in {"Completed", "Error", "Failed"}
            ],
        }
        if latest:
            state = latest["status"]
            row["backup"] = {
                "value": {
                    "name": latest["metadata"]["name"],
                    "recovery_point": state["snapshotCreatedAt"],
                    "age_seconds": age(state["snapshotCreatedAt"], now),
                    "backup_created_at": observed(
                        state.get("backupCreatedAt"),
                        "Longhorn has not reported the backup creation time.",
                    ),
                    "observed_at": observed(
                        state.get("lastSyncedAt"),
                        "Longhorn has not reported the backup observation time.",
                    ),
                }
            }
        else:
            row["backup"] = unknown(
                "No fully completed backup with a snapshot time was observed for this volume and target."
            )
        rows.append(row)
    return {
        "value": {
            "bound_claims": len(rows),
            "claims_with_backup_schedule": sum(bool(row.get("backup_schedules")) for row in rows),
            "claims_with_completed_backup": sum(
                row["backup"]["value"] != "unknown" for row in rows
            ),
            "claims": rows,
            "basis": "Current native Longhorn records. Schedule coverage is separate from successful backup coverage. Claims protected by another tool can have no Longhorn backup.",
        }
    }


def cnpg_report(data, now):
    clusters = items(data, "clusters")
    backups = items(data, "cnpg_backups")
    schedules = items(data, "cnpg_schedules")
    rows = []
    for cluster in sorted(clusters, key=identity):
        namespace, name = identity(cluster)

        matching = [b for b in backups if cluster_ref(b) == (namespace, name)]
        successful = [
            b
            for b in matching
            if b.get("status", {}).get("phase") == "completed"
            and timestamp(b["status"].get("startedAt")) is not None
        ]
        latest = max(successful, key=lambda b: timestamp(b["status"]["startedAt"]), default=None)
        conditions = {
            c["type"]: c["status"] for c in cluster.get("status", {}).get("conditions", [])
        }
        row = {
            "cluster": f"{namespace}/{name}",
            "schedules": [
                {
                    "name": s["metadata"]["name"],
                    "schedule": s["spec"].get("schedule"),
                    "suspended": s["spec"].get("suspend", False),
                }
                for s in schedules
                if cluster_ref(s) == (namespace, name)
            ],
            "continuous_archiving": observed(
                conditions.get("ContinuousArchiving"),
                "CNPG has not reported continuous archiving status.",
            ),
            "latest_wal_age_seconds": unknown(
                "The Cluster status has no last archived WAL time. A True condition does not prove WAL age."
            ),
            "failed_backups": [
                b["metadata"]["name"]
                for b in matching
                if b.get("status", {}).get("phase") == "failed"
            ],
            "unfinished_backups": [
                b["metadata"]["name"]
                for b in matching
                if b.get("status", {}).get("phase") not in {"completed", "failed"}
            ],
        }
        if latest:
            state = latest["status"]
            row["base_backup"] = {
                "value": {
                    "name": latest["metadata"]["name"],
                    "started_at": state["startedAt"],
                    "stopped_at": observed(
                        state.get("stoppedAt"), "CNPG has not reported the completion time."
                    ),
                    "age_seconds": age(state["startedAt"], now),
                    "method": observed(
                        state.get("method"), "CNPG has not reported the backup method."
                    ),
                }
            }
        else:
            row["base_backup"] = unknown("CNPG has no completed base backup with a start time.")
        rows.append(row)
    return {
        "value": rows,
        "basis": "Base backup age is not the PostgreSQL recovery-point age; WAL and restore checks are also required.",
    }


def read_resource(entry):
    key, (resource, namespace) = entry
    command = ["kubectl", "--request-timeout=10s", "get", resource, "-o", "json"]
    command.extend(["-n", namespace] if namespace else ["-A"])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
        value = json.loads(result.stdout)
        if not isinstance(value, dict) or not isinstance(value.get("items"), list):
            raise ValueError("The API did not return a resource list.")
    except subprocess.CalledProcessError as exc:
        value = unknown(f"Cannot read {resource}: {exc.stderr.strip() or str(exc)}")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        value = unknown(f"Cannot read {resource}: {exc}")
    return key, value


def read_observations():
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(read_resource, RESOURCES.items()))


def attach_restore_evidence(report, data, now, root=None, read_private=True):
    from scripts.app_recovery import app_recovery

    try:
        apps = items(data, "applications")
        report["restore_evidence"] = {
            "value": [
                {
                    "app": app["metadata"]["name"],
                    "claims": app_recovery(app, report, now, root, read_private)["last_restore"],
                }
                for app in sorted(apps, key=identity)
            ]
        }
    except (KeyError, TypeError, ValueError):
        report["restore_evidence"] = unknown(
            "Application observations are unavailable; restore reports cannot establish the app inventory."
        )


def build_report(data, now):
    report = {"schema_version": 1, "observed_at": now.isoformat()}
    for key, function in (("longhorn", longhorn_report), ("cnpg", cnpg_report)):
        try:
            report[key] = function(data, now)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            report[key] = unknown(f"Cannot establish {key} coverage: {exc}")
    report["restic"] = unknown(
        "No verified Restic snapshot observations are connected yet. CronJob schedules do not prove a successful paired backup."
    )
    report["restore_evidence"] = unknown(
        "No restore evidence source is connected yet. Native backup completion does not prove a restore."
    )
    report["seven_day_rpo"] = unknown(
        "This is one observation, not seven days of recovery-point measurements and restore evidence."
    )
    return report


def print_report(report):
    if "error" in report:
        print(display(report["error"]))
        return
    print(f"Observed: {report['observed_at']}")
    longhorn = report["longhorn"]["value"]
    if longhorn == "unknown":
        print(f"Longhorn: {display(report['longhorn'])}")
    else:
        print(
            f"Longhorn: {longhorn['claims_with_backup_schedule']} of {longhorn['bound_claims']} "
            f"bound claims have a backup schedule; "
            f"{longhorn['claims_with_completed_backup']} have a completed backup record."
        )
        for row in longhorn["claims"]:
            if row["backup"]["value"] == "unknown" and not row.get("backup_schedules"):
                continue
            backup = row["backup"]["value"]
            point = (
                display(row["backup"])
                if backup == "unknown"
                else (f"{backup['name']}, snapshot age {display(backup['age_seconds'])} seconds")
            )
            print(f"  {row['claim']}: {point}")
            print(
                f"    Target available: {display(row['target_available'])}; "
                f"failed records: {len(row['failed_backups'])}; "
                f"unfinished: {len(row['unfinished_backups'])}."
            )
        missing = longhorn["bound_claims"] - longhorn["claims_with_completed_backup"]
        if missing:
            print(
                f"  {missing} claims: unknown (no completed Longhorn backup observed; another tool may protect them). Use FORMAT=json for claim details."
            )
    cnpg = report["cnpg"]["value"]
    if cnpg == "unknown":
        print(f"CNPG: {display(report['cnpg'])}")
    else:
        for row in cnpg:
            backup = row["base_backup"]["value"]
            point = (
                display(row["base_backup"])
                if backup == "unknown"
                else (f"{backup['name']}, base backup age {display(backup['age_seconds'])} seconds")
            )
            print(f"CNPG {row['cluster']}: {point}")
            print(f"  WAL age: {display(row['latest_wal_age_seconds'])}")
            print(
                f"  Failed records: {len(row['failed_backups'])}; unfinished: {len(row['unfinished_backups'])}."
            )
    evidence = report["restore_evidence"]["value"]
    if evidence == "unknown":
        print(f"Restore evidence: {display(report['restore_evidence'])}")
    else:
        unmapped = []
        for app in evidence:
            claims = app["claims"]["value"]
            if claims == "unknown":
                unmapped.append(app["app"])
                continue
            for claim in claims:
                result = claim["evidence"]["value"]
                if result == "unknown":
                    print(f"Restore {app['app']} {claim['claim']}: {display(claim['evidence'])}")
                    continue
                success = result["last_success"]["value"]
                latest = result["last_attempt"]["value"]
                age_text = (
                    display(result["last_success"])
                    if success == "unknown"
                    else f"{success['age_seconds']} seconds ago"
                )
                attempt = (
                    display(result["last_attempt"])
                    if latest == "unknown"
                    else f"{latest['status']}, accepted={latest['accepted']}"
                )
                print(
                    f"Restore {app['app']} {claim['claim']}: last success {age_text}; latest attempt {attempt}."
                )
        if unmapped:
            print(
                f"Restore mapping unknown for {', '.join(unmapped)}: Application metadata has no valid data-claims mapping."
            )
    for key in ("restic", "seven_day_rpo"):
        print(f"{key}: {display(report[key])}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--input", help="Read saved observation JSON for an offline check.")
    parser.add_argument(
        "--restore-dir",
        help="Use a private restore report directory; enables report reads for offline input.",
    )
    args = parser.parse_args(argv)
    try:
        if args.input:
            data = json.loads(Path(args.input).read_text())
            if not isinstance(data, dict):
                raise ValueError("The observation bundle must be an object.")
        else:
            data = read_observations()
        now = datetime.now(timezone.utc)
        report = build_report(data, now)
        attach_restore_evidence(
            report, data, now, args.restore_dir, not args.input or args.restore_dir is not None
        )
        report["source"] = str(args.input) if args.input else "Native Kubernetes backup records"
    except (OSError, ValueError) as exc:
        report = {"error": unknown(f"Cannot read backup observations: {exc}")}
    code = (
        2
        if "error" in report
        or any(report[key]["value"] == "unknown" for key in ("longhorn", "cnpg"))
        or (not args.input and report["restore_evidence"]["value"] == "unknown")
        else 0
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
