"""Run an isolated Obsidian restore through the maintained Ansible recovery operations."""

import argparse
import base64
import fcntl
import hashlib
import json
import os
import re
import secrets
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scripts.backup_status import timestamp
from scripts.restore_common import identity, require, save_report
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
    started = datetime.now(timezone.utc)
    check_id = started.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
    state = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "soyspray/restores/obsidian-livesync"
    )
    output = state / check_id
    report = {
        "schema_version": 1,
        "app": "obsidian-livesync",
        "check_id": check_id,
        "started_at": started.isoformat(),
        "status": "running",
        "cleanup": "not started",
    }
    created_output = False
    operation_started = False
    lock = None
    stage = "preflight"
    try:
        require(
            not output.resolve().is_relative_to(ROOT),
            "Restore evidence must stay outside the checkout.",
        )
        output.mkdir(mode=0o700, parents=True)
        created_output = True
        state.chmod(0o700)
        lock = (state / ".lock").open("a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another Obsidian restore check is running.") from None
        save_report(output, report)
        print(f"Checking Obsidian recovery. Private logs: {output}", flush=True)
        with (output / "preflight.log").open("w") as log:
            subprocess.run(
                ["make", "go"],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=1200,
            )
        report["git_revision"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        for path in (args.vault_file, args.vault_password_file):
            require(
                path.is_file() and not path.resolve().is_relative_to(ROOT),
                "Use existing off-cluster Vault inputs and password files outside this checkout.",
            )
        require(
            args.vault_file.read_bytes().startswith(b"$ANSIBLE_VAULT;"),
            "The Obsidian input file must use Ansible Vault encryption.",
        )
        with tempfile.TemporaryDirectory(prefix="working-", dir=output) as directory:
            work = Path(directory)
            config = subprocess.check_output(
                ["kubectl", "config", "view", "--raw", "--minify", "--flatten", "-o", "json"],
                timeout=20,
                stderr=subprocess.PIPE,
            )
            kubeconfig = work / "kubeconfig.json"
            kubeconfig.write_bytes(config)
            env = {**os.environ, "KUBECONFIG": str(kubeconfig)}

            def kube(*args):
                return json.loads(
                    subprocess.check_output(
                        ["kubectl", "--request-timeout=15s", *args, "-o", "json"],
                        env=env,
                        stderr=subprocess.PIPE,
                        timeout=30,
                    )
                )

            stage = "backup and identity selection"
            claim = kube(
                "-n", "obsidian", "get", "pvc", "obsidian-livesync-couchdb-rescue-longhorn"
            )
            volume = kube("get", "pv", claim["spec"]["volumeName"])
            verify_binding(claim, volume)
            backup = select_backup(
                kube("-n", "longhorn-system", "get", "backups.longhorn.io")["items"],
                claim["spec"]["volumeName"],
                datetime.now(timezone.utc),
                args.backup,
            )
            point = timestamp(backup["status"]["snapshotCreatedAt"])
            report["backup"] = {
                "name": backup["metadata"]["name"],
                "uid": backup["metadata"]["uid"],
                "recovery_point": point.isoformat(),
                "age_at_selection_seconds": int(
                    (datetime.now(timezone.utc) - point).total_seconds()
                ),
            }
            report["source_claim_uid"] = claim["metadata"]["uid"]
            report["source_volume_uid"] = volume["metadata"]["uid"]
            runtime_secret = kube("-n", "obsidian", "get", "secret", "obsidian-livesync-couchdb")
            archived = yaml.safe_load(
                subprocess.check_output(
                    [
                        str(ROOT / "soyspray-venv/bin/ansible-vault"),
                        "view",
                        "--vault-password-file",
                        str(args.vault_password_file.resolve()),
                        str(args.vault_file.resolve()),
                    ],
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
            )
            inputs = runtime_values(archived, runtime_secret)
            secret_hash = hashlib.sha256(
                json.dumps(runtime_secret["data"], sort_keys=True).encode()
            ).hexdigest()
            deployment = kube(
                "-n", "obsidian", "get", "deployment", "obsidian-livesync-couchdb-hostpath-rescue"
            )
            require(
                deployment["spec"].get("replicas") == 1
                and deployment["spec"].get("strategy", {}).get("type") == "Recreate",
                "Obsidian must retain its single-writer deployment.",
            )
            pods = kube(
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
            container = next(
                item for item in pod["spec"]["containers"] if item["name"] == "couchdb"
            )
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
            config = kube("-n", "obsidian", "get", "configmap", "obsidian-livesync-couchdb")
            declared_config = yaml.safe_load(
                (ROOT / "apps/obsidian-livesync/manifests/configmap-couchdb.yaml").read_text()
            )
            require(
                config.get("data") == declared_config.get("data"),
                "The committed CouchDB configuration differs from live.",
            )
            report["image"] = image
            namespace = "restore-obsidian-" + check_id
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
                "recovery_check_id": check_id,
                "recovery_backup_name": backup["metadata"]["name"],
                "recovery_expected_claim_uid": claim["metadata"]["uid"],
                "recovery_expected_backup_uid": backup["metadata"]["uid"],
            }

            def ansible(playbook, log_name):
                variable_file = work / "operation-inputs.json"
                variable_file.write_text(json.dumps(variables))
                with (output / log_name).open("w") as log:
                    subprocess.run(
                        [
                            str(ROOT / "soyspray-venv/bin/ansible-playbook"),
                            "-i",
                            "kubespray/inventory/soycluster/hosts.yml",
                            "--become",
                            "--become-user=root",
                            "--user",
                            "ubuntu",
                            "playbooks/operations/recovery/" + playbook,
                            "-e",
                            "@" + str(variable_file),
                        ],
                        cwd=ROOT,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=3600,
                    )

            try:
                stage = "isolated Longhorn restore"
                operation_started = True
                report["scratch_namespace"] = namespace
                report["cleanup"] = "pending"
                save_report(output, report)
                print(f"Restoring {report['backup']['name']} into {namespace}.", flush=True)
                ansible("restore-volume.yml", "restore.log")
                restored = kube("-n", namespace, "get", "pvc", "restored-data")
                require(
                    restored["metadata"]["uid"] != claim["metadata"]["uid"]
                    and restored["spec"]["volumeName"] != claim["spec"]["volumeName"],
                    "The restore did not use an isolated claim and volume.",
                )
                report["restored_claim_uid"] = restored["metadata"]["uid"]
                stage = "isolated stock CouchDB startup"
                ansible("start-restored-app.yml", "start.log")
                stage = "restored note content checks"
                report["data"] = check_restored_notes(namespace, work, env, inputs)
                report["data"]["data_checks"] = "passed"
                stage = "original resource verification"
                require(
                    identity(
                        kube(
                            "-n",
                            "obsidian",
                            "get",
                            "pvc",
                            "obsidian-livesync-couchdb-rescue-longhorn",
                        )
                    )
                    == identity(claim)
                    and identity(kube("get", "pv", claim["spec"]["volumeName"])) == identity(volume)
                    and identity(
                        kube(
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
                current_secret = kube(
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
                current_config = kube(
                    "-n", "obsidian", "get", "configmap", "obsidian-livesync-couchdb"
                )
                require(
                    identity(current_config) == identity(config)
                    and current_config.get("data") == config.get("data"),
                    "The original CouchDB configuration changed during the check.",
                )
                report["original_resources"] = "unchanged"
            finally:
                if operation_started:
                    try:
                        ansible("cleanup-restore.yml", "cleanup.log")
                        report["cleanup"] = "completed"
                    except Exception:
                        stage = "isolated resource cleanup"
                        report["cleanup"] = "failed - inspect the guarded cleanup log"
                        raise
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["failed_stage"] = stage
        if isinstance(error, ValueError):
            report["cause"] = str(error)
        elif isinstance(error, subprocess.CalledProcessError):
            report["cause"] = f"{Path(error.cmd[0]).name} failed with exit {error.returncode}."
        elif isinstance(error, subprocess.TimeoutExpired):
            report["cause"] = f"{Path(error.cmd[0]).name} exceeded its time limit."
        elif isinstance(error, OSError):
            report["cause"] = error.strerror
        else:
            report["cause"] = "The operation did not complete because of an unexpected local error."
    if lock is not None:
        lock.close()
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["duration_seconds"] = int((datetime.now(timezone.utc) - started).total_seconds())
    if created_output:
        save_report(output, report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
