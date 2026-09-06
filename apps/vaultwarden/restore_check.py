"""Run an isolated Vaultwarden restore through the maintained Ansible recovery operations."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from apps.vaultwarden.check_restore import check_data, check_login
from scripts.backup_status import timestamp
from scripts.restore_common import identity, require, run_restore
from scripts.restore_common import select_backup as select_backup
from scripts.restore_common import verify_binding as verify_binding

ROOT = Path(__file__).resolve().parents[2]


def runtime_values(archived, live):
    email = archived.get("vaultwarden_agent_email")
    password = archived.get("vaultwarden_agent_master_password")
    require(
        email == "automation@vault.soyspray.vip" and isinstance(password, str) and password,
        "The encrypted restricted agent inputs are incomplete.",
    )
    for key, value in (("email", email), ("master-password", password)):
        require(
            live.get("data", {}).get(key) == base64.b64encode(value.encode()).decode(),
            "The archived restricted identity does not match the runtime Secret.",
        )
    return {"email": email, "password": password}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    recovery = Path.home() / ".config/soyspray/recovery"
    parser.add_argument("--vault-file", type=Path, default=recovery / "vaultwarden.vault.yml")
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
        claim = operation.kube("-n", "vaultwarden", "get", "pvc", "vaultwarden-data")
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
        runtime_secret = operation.kube(
            "-n", "vaultwarden", "get", "secret", "vaultwarden-agent-login"
        )
        inputs = runtime_values(operation.vault(), runtime_secret)
        secret_hash = hashlib.sha256(
            json.dumps(runtime_secret["data"], sort_keys=True).encode()
        ).hexdigest()
        deployment = operation.kube("-n", "vaultwarden", "get", "deployment", "vaultwarden")
        require(
            deployment["spec"].get("replicas") == 1
            and deployment["spec"].get("strategy", {}).get("type") == "Recreate",
            "Vaultwarden must retain its single-writer deployment.",
        )
        pods = operation.kube(
            "-n", "vaultwarden", "get", "pods", "-l", "app.kubernetes.io/name=vaultwarden"
        )["items"]
        require(
            len(pods) == 1 and not pods[0]["metadata"].get("deletionTimestamp"),
            "Vaultwarden has no single stable runtime pod.",
        )
        pod = pods[0]
        container = next(
            item for item in pod["spec"]["containers"] if item["name"] == "vaultwarden"
        )
        running = next(
            item for item in pod["status"]["containerStatuses"] if item["name"] == "vaultwarden"
        )
        image = container["image"]
        require(
            re.fullmatch(
                r"ghcr[.]io/dani-garcia/vaultwarden(?::[A-Za-z0-9._-]+)?@sha256:[0-9a-f]{64}",
                image,
            )
            and running.get("ready")
            and running.get("imageID", "").endswith(image.split("@", 1)[1]),
            "The Vaultwarden pod has not confirmed its pinned running image.",
        )
        operation.report["image"] = image
        namespace = "restore-vaultwarden-" + operation.check_id
        variables = {
            "recovery_app": "vaultwarden",
            "recovery_vaultwarden_image": image,
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
            operation.stage = "copy the idle restored database and WAL together"
            operation.run(
                [
                    "kubectl",
                    "cp",
                    "--retries=3",
                    "-c",
                    "inspect",
                    f"{namespace}/inspect:/data",
                    str(operation.work / "data"),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
                timeout=300,
            )
            operation.stage = "restored SQLite and attachment checks"
            operation.report["data"] = check_data(operation.work / "data")
            operation.stage = "isolated stock server startup"
            tls = operation.work / "tls"
            tls.mkdir()
            operation.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-days",
                    "2",
                    "-subj",
                    "/CN=localhost",
                    "-addext",
                    "subjectAltName=DNS:localhost,IP:127.0.0.1",
                    "-addext",
                    "basicConstraints=critical,CA:TRUE",
                    "-addext",
                    "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign",
                    "-keyout",
                    str(tls / "key.pem"),
                    "-out",
                    str(tls / "cert.pem"),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
                timeout=30,
            )
            variables["recovery_tls_directory"] = str(tls)
            operation.ansible("start-restored-app.yml", variables, "start.log")
            operation.stage = "restricted restored login and record decryption"
            operation.report["data"].update(
                check_login(namespace, operation.work, operation.env, inputs)
            )
            operation.report["data"]["data_checks"] = "passed"
            operation.stage = "original resource verification"
            require(
                identity(operation.kube("-n", "vaultwarden", "get", "pvc", "vaultwarden-data"))
                == identity(claim)
                and identity(operation.kube("get", "pv", claim["spec"]["volumeName"]))
                == identity(volume)
                and identity(
                    operation.kube("-n", "vaultwarden", "get", "deployment", "vaultwarden")
                )
                == identity(deployment),
                "The original Vaultwarden claim, volume, or deployment changed during the check.",
            )
            current_secret = operation.kube(
                "-n", "vaultwarden", "get", "secret", "vaultwarden-agent-login"
            )
            require(
                current_secret["metadata"]["uid"] == runtime_secret["metadata"]["uid"]
                and hashlib.sha256(
                    json.dumps(current_secret["data"], sort_keys=True).encode()
                ).hexdigest()
                == secret_hash,
                "The Vaultwarden runtime identity changed during the check.",
            )
            operation.report["original_resources"] = "unchanged"

    return run_restore("vaultwarden", ROOT, args.vault_file, args.vault_password_file, worker)


if __name__ == "__main__":
    raise SystemExit(main())
