"""Run an isolated Obsidian restore through the maintained Ansible recovery operations."""

import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path

import yaml

from scripts.backup_status import timestamp
from scripts.restore_common import identity, require, run_restore
from scripts.restore_common import select_backup as select_backup
from scripts.restore_common import verify_binding as verify_binding

from .check_restore import check_restored_notes

ROOT = Path(__file__).resolve().parents[2]


def runtime_values(archived, live):
    values = archived.get("obsidian_couchdb_identity")
    keys = {"adminUsername", "adminPassword", "cookieAuthSecret", "erlangCookie"}
    require(
        isinstance(values, dict)
        and set(values) == keys
        and all(isinstance(value, str) and value for value in values.values()),
        "The encrypted CouchDB identity is incomplete.",
    )
    encoded = {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}
    require(live.get("data") == encoded, "The archived CouchDB identity differs from live.")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    recovery = Path.home() / ".config/soyspray/recovery"
    parser.add_argument("--vault-file", type=Path, default=recovery / "obsidian.vault.yml")
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
        claim = operation.kube(
            "-n", "obsidian", "get", "pvc", "obsidian-livesync-couchdb-rescue-longhorn"
        )
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
            "-n", "obsidian", "get", "secret", "obsidian-livesync-couchdb"
        )
        inputs = runtime_values(operation.vault(), runtime_secret)
        secret_hash = hashlib.sha256(
            json.dumps(runtime_secret["data"], sort_keys=True).encode()
        ).hexdigest()
        deployment = operation.kube(
            "-n", "obsidian", "get", "deployment", "obsidian-livesync-couchdb-hostpath-rescue"
        )
        require(
            deployment["spec"].get("replicas") == 1
            and deployment["spec"].get("strategy", {}).get("type") == "Recreate",
            "Obsidian must retain its single-writer deployment.",
        )
        pods = operation.kube(
            "-n",
            "obsidian",
            "get",
            "pods",
            "-l",
            ",".join(
                f"{key}={value}"
                for key, value in sorted(deployment["spec"]["selector"]["matchLabels"].items())
            ),
        )["items"]
        require(
            len(pods) == 1 and not pods[0]["metadata"].get("deletionTimestamp"),
            "Obsidian has no single stable runtime pod.",
        )
        pod = pods[0]
        container = next(item for item in pod["spec"]["containers"] if item["name"] == "couchdb")
        running = next(
            item for item in pod["status"]["containerStatuses"] if item["name"] == "couchdb"
        )
        require(
            re.fullmatch(
                r"(?:docker[.]io/library/)?couchdb(?::[A-Za-z0-9._-]+)?(?:@sha256:[0-9a-f]{64})?",
                container["image"],
            )
            and running.get("ready"),
            "The CouchDB pod is not a ready stock image.",
        )
        observed = running.get("imageID", "").removeprefix("docker-pullable://")
        require(
            re.fullmatch(r"(?:docker[.]io/library/)?couchdb@sha256:[0-9a-f]{64}", observed),
            "The running CouchDB image digest is unavailable.",
        )
        image = "couchdb@" + observed.split("@", 1)[1]
        config = operation.kube("-n", "obsidian", "get", "configmap", "obsidian-livesync-couchdb")
        declared_config = yaml.safe_load(
            (ROOT / "apps/obsidian-livesync/manifests/configmap-couchdb.yaml").read_text()
        )
        require(
            config.get("data") == declared_config.get("data"),
            "The committed CouchDB configuration differs from live.",
        )
        operation.report["image"] = image
        namespace = "restore-obsidian-" + operation.check_id
        variables = {
            "recovery_app": "obsidian",
            "recovery_couchdb_image": image,
            "recovery_resources": [
                {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "metadata": {"name": "obsidian-livesync-couchdb", "namespace": "obsidian"},
                    "data": runtime_secret["data"],
                },
                {
                    "apiVersion": "v1",
                    "kind": "ConfigMap",
                    "metadata": {"name": "obsidian-livesync-couchdb", "namespace": "obsidian"},
                    "data": declared_config["data"],
                },
            ],
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
            operation.stage = "isolated stock CouchDB startup"
            operation.ansible("start-restored-app.yml", variables, "start.log")
            operation.stage = "restored note content checks"
            operation.report["data"] = check_restored_notes(
                namespace, operation.work, operation.env, inputs
            )
            operation.report["data"]["data_checks"] = "passed"
            operation.stage = "original resource verification"
            require(
                identity(
                    operation.kube(
                        "-n", "obsidian", "get", "pvc", "obsidian-livesync-couchdb-rescue-longhorn"
                    )
                )
                == identity(claim)
                and identity(operation.kube("get", "pv", claim["spec"]["volumeName"]))
                == identity(volume)
                and identity(
                    operation.kube(
                        "-n",
                        "obsidian",
                        "get",
                        "deployment",
                        "obsidian-livesync-couchdb-hostpath-rescue",
                    )
                )
                == identity(deployment),
                "The original Obsidian claim, volume, or deployment changed during the check.",
            )
            current_secret = operation.kube(
                "-n", "obsidian", "get", "secret", "obsidian-livesync-couchdb"
            )
            require(
                current_secret["metadata"]["uid"] == runtime_secret["metadata"]["uid"]
                and hashlib.sha256(
                    json.dumps(current_secret["data"], sort_keys=True).encode()
                ).hexdigest()
                == secret_hash,
                "The Obsidian runtime identity changed during the check.",
            )
            current_config = operation.kube(
                "-n", "obsidian", "get", "configmap", "obsidian-livesync-couchdb"
            )
            require(
                identity(current_config) == identity(config)
                and current_config.get("data") == config.get("data"),
                "The original CouchDB configuration changed during the check.",
            )
            operation.report["original_resources"] = "unchanged"

    return run_restore("obsidian-livesync", ROOT, args.vault_file, args.vault_password_file, worker)


if __name__ == "__main__":
    raise SystemExit(main())
