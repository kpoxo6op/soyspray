"""Small shared checks for isolated Longhorn recovery operations."""

import json

from scripts.backup_status import has_backup_error, timestamp


def require(value, cause):
    if not value:
        raise ValueError(cause)


def select_backup(backups, volume, now, requested=None):
    candidates = []
    for backup in backups:
        state = backup.get("status", {})
        point = timestamp(state.get("snapshotCreatedAt"))
        if (
            state.get("volumeName") == volume
            and state.get("backupTargetName") == "critical-s3"
            and state.get("state") == "Completed"
            and state.get("progress") == 100
            and not has_backup_error(state)
            and point is not None
            and 0 < point.timestamp() <= now.timestamp()
            and state.get("url", "").startswith("s3://")
            and (requested is None or backup["metadata"]["name"] == requested)
        ):
            candidates.append(backup)
    require(candidates, "No eligible completed backup has a valid recovery point.")
    return max(candidates, key=lambda item: timestamp(item["status"]["snapshotCreatedAt"]))


def verify_binding(claim, volume):
    require(
        claim.get("status", {}).get("phase") == "Bound"
        and claim["spec"].get("storageClassName") == "longhorn"
        and volume["spec"].get("claimRef", {}).get("uid") == claim["metadata"]["uid"]
        and volume["spec"].get("csi", {}).get("driver") == "driver.longhorn.io"
        and volume["spec"]["csi"].get("volumeHandle") == claim["spec"]["volumeName"],
        "The original claim and Longhorn volume binding do not match.",
    )


def identity(item):
    return {"uid": item["metadata"]["uid"], "spec": item.get("spec")}


def save_report(output, report):
    temporary = output / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(output / "report.json")
