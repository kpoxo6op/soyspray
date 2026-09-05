"""Map native backup and private restore observations through Application metadata."""

import re

from scripts.app_status import PREFIX, unknown
from scripts.restore_evidence import read_evidence


def app_recovery(app, backup_report, now, restore_root=None, read_private=True):
    annotations = app.get("metadata", {}).get("annotations", {})
    declared = annotations.get(PREFIX + "data-claims", "")
    claims = [part.strip() for part in declared.split(",")]
    if (
        not declared
        or len(set(claims)) != len(claims)
        or any(
            not re.fullmatch(r"[a-z0-9][a-z0-9.-]*/[a-z0-9][a-z0-9.-]*", claim) for claim in claims
        )
    ):
        missing = unknown("Application metadata has no valid soyspray.vip/data-claims mapping.")
        return {"latest_backup": missing, "last_restore": missing}
    coverage = backup_report.get("longhorn", {}).get("value")
    rows = coverage.get("claims", []) if isinstance(coverage, dict) else []
    backups, restores = [], []
    for claim in claims:
        matches = [row for row in rows if row.get("claim") == claim]
        row = matches[0] if len(matches) == 1 else {}
        backups.append(
            {
                "claim": claim,
                "backup": row.get(
                    "backup",
                    unknown("No unique native backup observation matches the declared claim."),
                ),
                "failed_backups": row.get(
                    "failed_backups", unknown("Backup failures were not observed.")
                ),
                "target_available": row.get(
                    "target_available", unknown("Backup target availability was not observed.")
                ),
            }
        )
        evidence = (
            read_evidence(
                app["metadata"]["name"], row.get("claim_uid"), row.get("pv_uid"), now, restore_root
            )
            if read_private
            else unknown(
                "Offline status does not read private reports unless --restore-dir is supplied."
            )
        )
        restores.append({"claim": claim, "evidence": evidence})
    return {"latest_backup": {"value": backups}, "last_restore": {"value": restores}}
