"""Run the maintained Immich restore with shared locking and interruption cleanup."""

import hashlib
import json
import os
import secrets
from pathlib import Path

from scripts.restore_common import identity, require, run_restore

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = Path.home() / ".config/soyspray/recovery"


def restore(operation):
    resources = [
        ("deployment", "immich-server", "immich"),
        ("pvc", "immich-library", "immich"),
        ("service", "immich-db-active", "postgresql"),
        ("cluster.postgresql.cnpg.io", "immich-db-a", "postgresql"),
        ("secret", "immich-paired-backup", "immich"),
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

    before = fingerprints()
    variables = {
        "recovery_check_id": operation.check_id,
        "recovery_db_password": secrets.token_hex(24),
        "recovery_server_image_digest": "ghcr.io/immich-app/immich-server:v2.3.1@sha256:f8d06a32b1b2a81053d78e40bf8e35236b9faefb5c3903ce9ca8712c9ed78445",
    }

    def playbook(name, log):
        path = os.path.relpath(
            ROOT / "apps/immich/recovery" / name, ROOT / "playbooks/operations/recovery"
        )
        operation.ansible(path, variables, log)

    operation.stage = "isolated restore"
    try:
        playbook("restore.yml", "restore.log")
        report = json.loads((operation.output / "report.json").read_text())
        require(report.get("status") == "passed", "The isolated restore did not pass.")
        operation.report.update(report)
    finally:
        operation.stage = "isolated resource cleanup"
        try:
            playbook("cleanup.yml", "cleanup.log")
            operation.report["cleanup"] = "completed"
        except BaseException:
            operation.report["cleanup"] = "failed - inspect cleanup.log"
            raise
        finally:
            unchanged = fingerprints() == before
            operation.report["original_resources"] = "unchanged" if unchanged else "changed"
            require(unchanged, "Production identities changed during the restore.")


if __name__ == "__main__":
    raise SystemExit(
        run_restore(
            "immich", ROOT, PRIVATE / "immich-backup.vault.yml", PRIVATE / "vault-password", restore
        )
    )
