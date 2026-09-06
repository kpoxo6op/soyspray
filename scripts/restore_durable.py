"""Restore the daily small-volume backups through the shared isolated runner."""

import argparse
import json
import os
from pathlib import Path

import yaml

from scripts.restore_common import identity, require, run_restore, select_backup, verify_binding

ROOT = Path(__file__).resolve().parents[1]
NATIVE_APPS = (
    "booklore-mariadb",
    "dispatcharr-data",
    "redis-data-redis-master-0",
    "mosquitto-data",
)


def main():
    os.umask(0o077)
    recovery = Path.home() / ".config/soyspray/recovery"
    claims = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/recovery-claims.yml").read_text()
    )["recovery_claims"]
    targets = {
        key: value
        for key, value in claims.items()
        if key not in {"boys", "vaultwarden", "obsidian"}
    }

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app", nargs="+", choices=sorted(targets), help="Check only these daily volumes"
    )
    args = parser.parse_args()
    if args.app:
        targets = {name: targets[name] for name in dict.fromkeys(args.app)}

    def worker(operation):
        operation.report["volumes"] = []
        for app, target in targets.items():
            namespace, name = target["namespace"], target["claim"]
            claim = operation.kube("-n", namespace, "get", "pvc", name)
            pv = operation.kube("get", "pv", claim["spec"]["volumeName"])
            verify_binding(claim, pv)
            backup = select_backup(
                operation.kube("-n", "longhorn-system", "get", "backups.longhorn.io")["items"],
                claim["spec"]["volumeName"],
                operation.now(),
            )
            operation.report["backup"] = {
                "name": backup["metadata"]["name"],
                "uid": backup["metadata"]["uid"],
                "recovery_point": backup["status"]["snapshotCreatedAt"],
            }
            variables = {
                "recovery_app": app,
                "recovery_check_id": operation.check_id,
                "recovery_backup_name": backup["metadata"]["name"],
                "recovery_expected_claim_uid": claim["metadata"]["uid"],
                "recovery_expected_backup_uid": backup["metadata"]["uid"],
            }
            scratch = "restore-" + app + "-" + operation.check_id
            with operation.isolated_restore(scratch, variables):
                operation.stage = app + " isolated restore"
                operation.ansible("restore-volume.yml", variables, app + "-restore.log")
                destination = operation.work / app
                operation.stage = app + " restored file copy"
                with (operation.output / (app + "-copy.log")).open("wb") as log:
                    operation.run(
                        [
                            "kubectl",
                            "cp",
                            "--retries=3",
                            "-c",
                            "inspect",
                            scratch + "/inspect:/data",
                            str(destination),
                        ],
                        check=True,
                        stdout=log,
                        stderr=log,
                        timeout=900,
                    )
                operation.stage = app + " data verification"
                result = operation.run(
                    [
                        str(ROOT / "soyspray-venv/bin/python"),
                        str(ROOT / "scripts/check_durable_data.py"),
                        str(destination),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
                (operation.output / (app + "-data-errors.log")).write_text(result.stderr)
                require(
                    result.returncode == 0,
                    "The restored data check failed; inspect its private error log.",
                )
                data = json.loads(result.stdout)
                require(
                    identity(operation.kube("-n", namespace, "get", "pvc", name)) == identity(claim)
                    and identity(operation.kube("get", "pv", claim["spec"]["volumeName"]))
                    == identity(pv),
                    "The production claim or volume changed.",
                )
                if app in NATIVE_APPS:
                    candidates = []
                    for pod in operation.kube("-n", namespace, "get", "pods")["items"]:
                        mounts = {
                            v["name"]
                            for v in pod["spec"].get("volumes", [])
                            if v.get("persistentVolumeClaim", {}).get("claimName") == name
                        }
                        for container in pod["spec"]["containers"]:
                            if mounts.intersection(
                                m["name"] for m in container.get("volumeMounts", [])
                            ):
                                status = next(
                                    c
                                    for c in pod["status"].get("containerStatuses", [])
                                    if c["name"] == container["name"]
                                )
                                if status.get("ready"):
                                    candidates.append(
                                        status["imageID"].removeprefix("docker-pullable://")
                                    )
                    require(
                        len(candidates) == 1, "The native runtime image is not uniquely identified."
                    )
                    variables.update(
                        recovery_native_image=candidates[0],
                        recovery_original_volume=claim["spec"]["volumeName"],
                    )
                    try:
                        operation.ansible("validate-durable.yml", variables, app + "-native.log")
                    finally:
                        log = operation.run(
                            ["kubectl", "-n", scratch, "logs", "job/native-check"],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        (operation.output / (app + "-native-output.log")).write_text(
                            log.stdout + log.stderr
                        )
                    data["native_validation"] = "passed"
                    data["native_image"] = candidates[0]
                    data.pop("limits", None)
                operation.report["volumes"].append(
                    {
                        "app": app,
                        "backup": dict(operation.report["backup"]),
                        "source_claim_uid": claim["metadata"]["uid"],
                        "source_volume_uid": pv["metadata"]["uid"],
                        "data": data,
                        "original_resources": "unchanged",
                    }
                )
            (operation.output / "cleanup.log").rename(operation.output / (app + "-cleanup.log"))
            operation.report["volumes"][-1]["cleanup"] = operation.report["cleanup"]
            require(operation.report["cleanup"] == "completed", "Scratch cleanup did not complete.")

    return run_restore(
        "durable", ROOT, recovery / "longhorn.vault.yml", recovery / "vault-password", worker
    )


if __name__ == "__main__":
    raise SystemExit(main())
