"""Run an isolated Boys restore through the maintained Ansible recovery operations."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from scripts.backup_status import timestamp
from scripts.restore_common import identity, require, run_restore
from scripts.restore_common import select_backup as select_backup
from scripts.restore_common import verify_binding as verify_binding

ROOT = Path(__file__).resolve().parents[2]


def runtime_values(archived, live):
    values = {name: archived.get(name) for name in ("boys_pin", "boys_session_key")}
    require(
        isinstance(values["boys_pin"], str) and isinstance(values["boys_session_key"], str),
        "The encrypted Boys runtime inputs are incomplete.",
    )
    for key, name in (("pin", "boys_pin"), ("session-key", "boys_session_key")):
        require(
            live.get("data", {}).get(key) == base64.b64encode(values[name].encode()).decode(),
            "The archived Boys identity does not match the current runtime Secret.",
        )
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    recovery = Path.home() / ".config/soyspray/recovery"
    parser.add_argument("--vault-file", type=Path, default=recovery / "boys-runtime.vault.yml")
    parser.add_argument(
        "--vault-password-file",
        type=Path,
        default=Path(os.environ.get("ANSIBLE_VAULT_PASSWORD_FILE", recovery / "vault-password")),
    )
    parser.add_argument(
        "--backup", help="Check this completed backup instead of the newest eligible one."
    )
    args = parser.parse_args()
    os.umask(0o077)

    def worker(operation):
        operation.stage = "backup and identity selection"
        claim = operation.kube("-n", "boys", "get", "pvc", "boys-data")
        volume = operation.kube("get", "pv", claim["spec"]["volumeName"])
        verify_binding(claim, volume)
        backup = select_backup(
            operation.kube("-n", "longhorn-system", "get", "backups.longhorn.io")["items"],
            claim["spec"]["volumeName"],
            operation.now(),
            args.backup,
        )
        point = timestamp(backup["status"]["snapshotCreatedAt"])
        operation.report["backup"] = {
            "name": backup["metadata"]["name"],
            "uid": backup["metadata"]["uid"],
            "recovery_point": point.isoformat(),
            "age_at_selection_seconds": int((operation.now() - point).total_seconds()),
        }
        operation.report["source_claim_uid"] = claim["metadata"]["uid"]
        operation.report["source_volume_uid"] = volume["metadata"]["uid"]
        runtime_secret = operation.kube("-n", "boys", "get", "secret", "boys-runtime")
        inputs = runtime_values(operation.vault(), runtime_secret)
        secret_hash = hashlib.sha256(
            json.dumps(runtime_secret["data"], sort_keys=True).encode()
        ).hexdigest()
        deployment = operation.kube("-n", "boys", "get", "deployment", "boys")
        require(
            deployment["spec"].get("replicas") == 1
            and deployment["spec"].get("strategy", {}).get("type") == "Recreate",
            "Boys must retain its single-writer deployment.",
        )
        pods = operation.kube("-n", "boys", "get", "pods", "-l", "boys-component=web")["items"]
        require(
            len(pods) == 1 and not pods[0]["metadata"].get("deletionTimestamp"),
            "Boys has no single stable runtime pod.",
        )
        pod = pods[0]
        container = next(item for item in pod["spec"]["containers"] if item["name"] == "web")
        running = next(item for item in pod["status"]["containerStatuses"] if item["name"] == "web")
        image = container["image"]
        require(
            re.fullmatch(r"ghcr.io/kpoxo6op/boys@sha256:[0-9a-f]{64}", image)
            and running.get("ready")
            and running.get("imageID", "").endswith(image.split("@", 1)[1]),
            "The Boys pod has not confirmed its pinned running image.",
        )
        operation.report["image"] = image
        namespace = "restore-boys-" + operation.check_id
        variables = {
            "recovery_app": "boys",
            "recovery_check_id": operation.check_id,
            "recovery_backup_name": backup["metadata"]["name"],
            "recovery_expected_claim_uid": claim["metadata"]["uid"],
            "recovery_expected_backup_uid": backup["metadata"]["uid"],
        }
        with operation.isolated_restore(namespace, variables):
            operation.stage = "isolated Longhorn restore"
            operation.ansible("restore-volume.yml", variables, "restore.log")
            restored = operation.kube("-n", namespace, "get", "pvc", "restored-data")
            require(
                restored["metadata"]["uid"] != claim["metadata"]["uid"]
                and restored["spec"]["volumeName"] != claim["spec"]["volumeName"],
                "The restore did not use an isolated claim and volume.",
            )
            operation.report["restored_claim_uid"] = restored["metadata"]["uid"]
            operation.stage = "copy restored data and deployed runtime"
            for source, target, container_name in (
                (f"{namespace}/inspect:/data", operation.work / "data", "inspect"),
                (f"boys/{pod['metadata']['name']}:/app", operation.work / "runtime", "web"),
            ):
                operation.run(
                    ["kubectl", "cp", "--retries=3", "-c", container_name, source, str(target)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=300,
                )
            operation.stage = "restored application data checks"
            checked = operation.run(
                [
                    sys.executable,
                    str(ROOT / "apps/boys/check_restore.py"),
                    "--database",
                    str(operation.work / "data/boys.sqlite3"),
                    "--runtime",
                    str(operation.work / "runtime"),
                ],
                input=json.dumps(inputs),
                capture_output=True,
                text=True,
                timeout=120,
            )
            operation.report["data"] = json.loads(checked.stdout)
            require(
                checked.returncode == 0 and operation.report["data"].get("data_checks") == "passed",
                "The restored application data check failed.",
            )
            operation.stage = "original resource verification"
            require(
                identity(operation.kube("-n", "boys", "get", "pvc", "boys-data")) == identity(claim)
                and identity(operation.kube("get", "pv", claim["spec"]["volumeName"]))
                == identity(volume)
                and identity(operation.kube("-n", "boys", "get", "deployment", "boys"))
                == identity(deployment),
                "The original Boys claim, volume, or deployment changed during the check.",
            )
            current_secret = operation.kube("-n", "boys", "get", "secret", "boys-runtime")
            require(
                current_secret["metadata"]["uid"] == runtime_secret["metadata"]["uid"]
                and hashlib.sha256(
                    json.dumps(current_secret["data"], sort_keys=True).encode()
                ).hexdigest()
                == secret_hash,
                "The Boys runtime identity changed during the check.",
            )
            operation.report["original_resources"] = "unchanged"

    return run_restore("boys", ROOT, args.vault_file, args.vault_password_file, worker)


if __name__ == "__main__":
    raise SystemExit(main())
