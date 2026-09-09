"""Run the maintained Immich restore with shared locking and interruption cleanup."""

import hashlib
import json
import os
import secrets
from pathlib import Path

from scripts.restore_common import identity, require, run_restore, save_report

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = Path.home() / ".config/soyspray/recovery"


def restore(operation):
    resources = [
        ("deployment", "immich-server", "immich"),
        ("pvc", "immich-library", "immich"),
        ("service", "immich-db-active", "postgresql"),
        ("cluster.postgresql.cnpg.io", "immich-db-a", "postgresql"),
    ]

    def fingerprints():
        result = []
        for kind, name, namespace in resources:
            resource = operation.kube("get", kind, name, "-n", namespace)
            result.append(
                (
                    identity(resource),
                    hashlib.sha256(
                        json.dumps(resource.get("data"), sort_keys=True).encode()
                    ).hexdigest(),
                )
            )
        return result

    compare_production = os.environ.get("SOYSPRAY_COMPARE_PRODUCTION") == "1"
    before = fingerprints() if compare_production else None
    vault = operation.vault()
    credentials = vault.get("immich_restic_credentials", {})
    expected_credential_keys = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "RESTIC_REPOSITORY",
        "RESTIC_PASSWORD",
    }
    require(
        isinstance(credentials, dict)
        and set(credentials) == expected_credential_keys
        and all(isinstance(value, str) and value for value in credentials.values()),
        "The encrypted Immich recovery input is incomplete.",
    )
    variables = {
        "recovery_check_id": operation.check_id,
        "recovery_db_password": secrets.token_hex(24),
        "recovery_restic_credentials": credentials,
        "recovery_server_image_digest": "ghcr.io/immich-app/immich-server:v2.3.1@sha256:f8d06a32b1b2a81053d78e40bf8e35236b9faefb5c3903ce9ca8712c9ed78445",
    }

    def playbook(name, log):
        path = os.path.relpath(
            ROOT / "apps/immich/recovery" / name, ROOT / "playbooks/operations/recovery"
        )
        operation.ansible(path, variables, log)

    operation.report["cleanup"] = "pending"
    operation.report["scratch_namespace"] = "immich-recovery-" + operation.check_id
    save_report(operation.output, operation.report)
    operation.stage = "isolated restore"
    try:
        playbook("restore.yml", "restore.log")
        report = json.loads((operation.output / "report.json").read_text())
        require(report.get("status") == "passed", "The isolated restore did not pass.")
        operation.report.update(report)
    finally:
        try:
            playbook("cleanup.yml", "cleanup.log")
            operation.report["cleanup"] = "completed"
        except BaseException:
            operation.stage = "isolated resource cleanup"
            operation.report["cleanup"] = "failed - inspect cleanup.log"
            raise
        finally:
            if before is None:
                operation.report["production_comparison"] = "not requested"
            else:
                unchanged = fingerprints() == before
                operation.report["production_comparison"] = "unchanged" if unchanged else "changed"
                require(unchanged, "Production identities changed during the restore.")


if __name__ == "__main__":
    raise SystemExit(
        run_restore(
            "immich",
            ROOT,
            PRIVATE / "immich-backup.vault.yml",
            PRIVATE / "vault-password",
            restore,
            explicit_target=True,
        )
    )
