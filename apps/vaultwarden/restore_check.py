"""Run an isolated Vaultwarden restore through the maintained Ansible recovery operations."""

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

from apps.vaultwarden.check_restore import check_data, check_login
from scripts.backup_status import timestamp
from scripts.restore_common import identity, require, save_report
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
    started = datetime.now(timezone.utc)
    check_id = started.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
    state = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "soyspray/restores/vaultwarden"
    )
    output = state / check_id
    report = {
        "schema_version": 1,
        "app": "vaultwarden",
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
            raise ValueError("Another Vaultwarden restore check is running.") from None
        save_report(output, report)
        print(f"Checking Vaultwarden recovery. Private logs: {output}", flush=True)
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
            "The Vaultwarden input file must use Ansible Vault encryption.",
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
            claim = kube("-n", "vaultwarden", "get", "pvc", "vaultwarden-data")
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
            runtime_secret = kube("-n", "vaultwarden", "get", "secret", "vaultwarden-agent-login")
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
            deployment = kube("-n", "vaultwarden", "get", "deployment", "vaultwarden")
            require(
                deployment["spec"].get("replicas") == 1
                and deployment["spec"].get("strategy", {}).get("type") == "Recreate",
                "Vaultwarden must retain its single-writer deployment.",
            )
            pods = kube(
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
            report["image"] = image
            namespace = "restore-vaultwarden-" + check_id
            variables = {
                "recovery_app": "vaultwarden",
                "recovery_vaultwarden_image": image,
                "recovery_check_id": check_id,
                "recovery_backup_name": backup["metadata"]["name"],
                "recovery_expected_claim_uid": claim["metadata"]["uid"],
                "recovery_expected_backup_uid": backup["metadata"]["uid"],
            }

            def ansible(playbook, log_name):
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
                            json.dumps(variables),
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
                stage = "copy the idle restored database and WAL together"
                subprocess.run(
                    [
                        "kubectl",
                        "cp",
                        "--retries=3",
                        "-c",
                        "inspect",
                        f"{namespace}/inspect:/data",
                        str(work / "data"),
                    ],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=300,
                )
                stage = "restored SQLite and attachment checks"
                report["data"] = check_data(work / "data")
                stage = "isolated stock server startup"
                tls = work / "tls"
                tls.mkdir()
                subprocess.run(
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
                ansible("start-restored-app.yml", "start.log")
                stage = "restricted restored login and record decryption"
                report["data"].update(check_login(namespace, work, env, inputs))
                report["data"]["data_checks"] = "passed"
                stage = "original resource verification"
                require(
                    identity(kube("-n", "vaultwarden", "get", "pvc", "vaultwarden-data"))
                    == identity(claim)
                    and identity(kube("get", "pv", claim["spec"]["volumeName"])) == identity(volume)
                    and identity(kube("-n", "vaultwarden", "get", "deployment", "vaultwarden"))
                    == identity(deployment),
                    "The original Vaultwarden claim, volume, or deployment changed during the check.",
                )
                current_secret = kube(
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
