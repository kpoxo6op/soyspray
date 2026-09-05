"""Run an isolated Boys restore through the maintained Ansible recovery operations."""

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from scripts.backup_status import has_backup_error, timestamp

ROOT = Path(__file__).resolve().parents[2]


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
    require(candidates, "No eligible completed Boys backup has a valid recovery point.")
    return max(candidates, key=lambda item: timestamp(item["status"]["snapshotCreatedAt"]))


def verify_binding(claim, volume):
    require(
        claim.get("status", {}).get("phase") == "Bound"
        and claim["spec"].get("storageClassName") == "longhorn"
        and volume["spec"].get("claimRef", {}).get("uid") == claim["metadata"]["uid"]
        and volume["spec"].get("csi", {}).get("driver") == "driver.longhorn.io"
        and volume["spec"]["csi"].get("volumeHandle") == claim["spec"]["volumeName"],
        "The original Boys claim and Longhorn volume binding do not match.",
    )


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


def identity(item):
    return {"uid": item["metadata"]["uid"], "spec": item.get("spec")}


def save_report(output, report):
    temporary = output / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(output / "report.json")


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
    started = datetime.now(timezone.utc)
    check_id = started.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
    state = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "soyspray/restores/boys"
    )
    output = state / check_id
    report = {
        "schema_version": 1,
        "app": "boys",
        "check_id": check_id,
        "started_at": started.isoformat(),
        "status": "running",
        "cleanup": "not started",
    }
    created_output = False
    operation_started = False
    stage = "preflight"
    try:
        require(
            not output.resolve().is_relative_to(ROOT),
            "Restore evidence must stay outside the checkout.",
        )
        output.mkdir(mode=0o700, parents=True)
        created_output = True
        state.chmod(0o700)
        save_report(output, report)
        print(f"Checking Boys recovery. Private logs: {output}", flush=True)
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
            "The Boys input file must use Ansible Vault encryption.",
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
            claim = kube("-n", "boys", "get", "pvc", "boys-data")
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
            runtime_secret = kube("-n", "boys", "get", "secret", "boys-runtime")
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
            deployment = kube("-n", "boys", "get", "deployment", "boys")
            require(
                deployment["spec"].get("replicas") == 1
                and deployment["spec"].get("strategy", {}).get("type") == "Recreate",
                "Boys must retain its single-writer deployment.",
            )
            pods = kube("-n", "boys", "get", "pods", "-l", "boys-component=web")["items"]
            require(
                len(pods) == 1 and not pods[0]["metadata"].get("deletionTimestamp"),
                "Boys has no single stable runtime pod.",
            )
            pod = pods[0]
            container = next(item for item in pod["spec"]["containers"] if item["name"] == "web")
            running = next(
                item for item in pod["status"]["containerStatuses"] if item["name"] == "web"
            )
            image = container["image"]
            require(
                re.fullmatch(r"ghcr.io/kpoxo6op/boys@sha256:[0-9a-f]{64}", image)
                and running.get("ready")
                and running.get("imageID", "").endswith(image.split("@", 1)[1]),
                "The Boys pod has not confirmed its pinned running image.",
            )
            report["image"] = image
            namespace = "restore-boys-" + check_id
            variables = {
                "recovery_app": "boys",
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
                stage = "copy restored data and deployed runtime"
                for source, target, container_name in (
                    (f"{namespace}/inspect:/data", work / "data", "inspect"),
                    (f"boys/{pod['metadata']['name']}:/app", work / "runtime", "web"),
                ):
                    subprocess.run(
                        ["kubectl", "cp", "--retries=3", "-c", container_name, source, str(target)],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        check=True,
                        timeout=300,
                    )
                stage = "restored application data checks"
                checked = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "apps/boys/check_restore.py"),
                        "--database",
                        str(work / "data/boys.sqlite3"),
                        "--runtime",
                        str(work / "runtime"),
                    ],
                    input=json.dumps(inputs),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                report["data"] = json.loads(checked.stdout)
                require(
                    checked.returncode == 0 and report["data"].get("data_checks") == "passed",
                    "The restored application data check failed.",
                )
                stage = "original resource verification"
                require(
                    identity(kube("-n", "boys", "get", "pvc", "boys-data")) == identity(claim)
                    and identity(kube("get", "pv", claim["spec"]["volumeName"])) == identity(volume)
                    and identity(kube("-n", "boys", "get", "deployment", "boys"))
                    == identity(deployment),
                    "The original Boys claim, volume, or deployment changed during the check.",
                )
                current_secret = kube("-n", "boys", "get", "secret", "boys-runtime")
                require(
                    current_secret["metadata"]["uid"] == runtime_secret["metadata"]["uid"]
                    and hashlib.sha256(
                        json.dumps(current_secret["data"], sort_keys=True).encode()
                    ).hexdigest()
                    == secret_hash,
                    "The Boys runtime identity changed during the check.",
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
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["duration_seconds"] = int((datetime.now(timezone.utc) - started).total_seconds())
    if created_output:
        save_report(output, report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
