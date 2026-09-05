"""Read private restore reports without treating backup completion as restore proof."""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from scripts.app_status import unknown


def default_root():
    return (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "soyspray/restores"
    )


def instant(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def read_evidence(app, claim_uid, pv_uid, now, root=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", app):
        return unknown("The Application name cannot identify a restore report folder.")
    if not claim_uid or not pv_uid:
        return unknown(
            "Observed claim and PV identities are unavailable; restore evidence cannot be bound."
        )
    directory = Path(root if root is not None else default_root()) / app
    try:
        if directory.is_symlink():
            return unknown("The Application restore directory is a symlink; reports were not read.")
        paths = list(directory.glob("*/report.json"))
        records = []
        invalid = 0
        for path in paths:
            try:
                if path.is_symlink() or path.parent.is_symlink():
                    raise ValueError("Report symlink")
                if path.stat().st_size > 1024 * 1024:
                    raise ValueError("Oversized report")
                record = json.loads(path.read_text())
                started = instant(record.get("started_at"))
                finished = instant(record.get("finished_at"))
                check_id = record.get("check_id", "")
                state = record.get("status")
                if (
                    record.get("schema_version") != 1
                    or record.get("app") != app
                    or check_id != path.parent.name
                    or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,23}", check_id)
                    or started is None
                    or started > now
                    or state not in {"running", "passed", "failed"}
                    or not isinstance(record.get("data", {}), dict)
                    or not isinstance(record.get("backup", {}), dict)
                    or not isinstance(record.get("image", ""), str)
                    or (state != "running" and (finished is None or not started <= finished <= now))
                ):
                    raise ValueError("Invalid report identity or times")
                records.append((started, record))
            except (OSError, ValueError, TypeError, AttributeError):
                invalid += 1
    except OSError:
        return unknown("The private restore evidence directory cannot be read.")
    if not records and not invalid:
        return unknown("No private restore report is available on this operator machine.")
    records.sort(key=lambda entry: (entry[0], entry[1]["check_id"]), reverse=True)

    def summary(record):
        matches = (
            record.get("source_claim_uid") == claim_uid
            and record.get("source_volume_uid") == pv_uid
        )
        data = record.get("data") or {}
        point = instant((record.get("backup") or {}).get("recovery_point"))
        finished = instant(record.get("finished_at"))
        valid = (
            record["status"] == "passed"
            and matches
            and record.get("cleanup") == "completed"
            and record.get("original_resources") == "unchanged"
            and data.get("data_checks") == "passed"
            and point is not None
            and point <= finished
            and re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", record.get("image", "")) is not None
        )
        result = {
            "check_id": record["check_id"],
            "started_at": record["started_at"],
            "status": record["status"],
            "matches_observed_claim_and_pv": matches,
            "accepted": bool(valid),
        }
        if finished:
            result.update(
                finished_at=record["finished_at"], age_seconds=int((now - finished).total_seconds())
            )
        if valid:
            result.update(
                image=record["image"],
                recovery_point=point.isoformat(),
                existing_browser_cookie=unknown(
                    "This report does not prove a saved browser-cookie check."
                ),
            )
            login_field = "human_personal_pin" if app == "boys" else "human_login"
            result[login_field] = unknown("This report does not prove a human login.")
            if app == "obsidian-livesync":
                fields = (
                    "active_plain_notes",
                    "readable_plain_notes",
                    "unreadable_plain_notes",
                    "pre_existing_missing_chunks",
                    "active_binary_documents",
                    "legacy_note_documents",
                )
                result["data_coverage"] = {
                    key: {"value": data[key]}
                    if type(data.get(key)) is int and data[key] >= 0
                    else unknown("This report does not record a valid count.")
                    for key in fields
                }
                result["data_coverage"]["attachment_recovery"] = unknown(
                    "The maintained check reads plain notes; binary attachment recovery is not verified."
                )
        else:
            result["cause"] = (
                "The attempt did not complete successfully against the observed claim and PV with data checks and cleanup."
            )
        return result

    summaries = [summary(record) for _, record in records]
    last_success = next((record for record in summaries if record["accepted"]), None)
    return {
        "value": {
            "last_attempt": unknown(
                "A private report is invalid or unreadable; the latest attempt is uncertain."
            )
            if invalid
            else {"value": summaries[0]},
            "last_success": {"value": last_success}
            if last_success
            else unknown(
                "No completed data restore with cleanup matches the observed claim and PV."
            ),
            "invalid_reports": invalid,
            "basis": "Private operator reports matched to observed storage identities. This is historical evidence for the reported image, not seven-day RPO or a current user-login check.",
        }
    }
