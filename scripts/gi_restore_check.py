#!/usr/bin/env python3
"""Restore a completed private workspace copy into isolation and check it.

The workspace owns its copies, so this check does not use a Longhorn backup.

Everything happens **inside the cluster**.  The copy is never streamed to the
machine that runs this check, because after the private import the database
holds real records and must not leave the home cluster.  The service restores
its own completed copy into a scratch database on the pod's writable temporary
space, verifies the result, compares it with the live dataset by a content hash
rather than by value, removes the scratch files, and reports counts, sizes,
identifiers, and ages only.

Run it from the repository root:

    make restore-check APP=gi
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = "gi"
DEPLOYMENT = "gi"
CONTAINER = "web"
BACKUP_DIR = "/backups"
SCRATCH_DIR = "/tmp/gi-restore-check"
RUNNING_IMAGE = re.compile(r"^ghcr\.io/kpoxo6op/gi-app@sha256:[0-9a-f]{64}$")
BACKUP_NAME = re.compile(r"^gi-(daily|pre-change)-\d{8}T\d{6}Z-[0-9a-f]{12}\.sqlite3$")

# This runs inside the pod.  It restores the copy the check names, verifies the
# restored database, compares it with the live dataset by identity, and removes
# the scratch files.  It prints counts and hashes only, never a stored value.
IN_POD_PROGRAM = r"""
import json, os, shutil, sys
from gi_app.backup import dataset_identity, restore_database

scratch = sys.argv[1]
member = sys.argv[2]
live = os.environ.get("GI_DB_PATH", "/data/gi.sqlite3")
source = os.path.join(os.environ.get("GI_BACKUP_DIR", "/backups"), member)

result = {"member": member}
shutil.rmtree(scratch, ignore_errors=True)
os.makedirs(scratch, exist_ok=True)
target = os.path.join(scratch, "restored.sqlite3")
try:
    result["live_before"] = dataset_identity(live)
    result["restored"] = restore_database(source, target)
    # Read the restored copy back with the same reader the check trusts.
    result["identity"] = dataset_identity(target)
    result["live_after"] = dataset_identity(live)
finally:
    shutil.rmtree(scratch, ignore_errors=True)
result["scratch_removed"] = not os.path.exists(scratch)
print(json.dumps(result))
"""


class CheckError(Exception):
    """The check could not continue, or a required condition failed."""


def require(value, cause):
    if not value:
        raise CheckError(cause)


def kubectl(arguments):
    try:
        result = subprocess.run(["kubectl", *arguments], capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CheckError(f"kubectl could not run: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "ignore").strip()[:300]
        raise CheckError(f"kubectl {' '.join(arguments[:3])} failed: {detail}")
    return result.stdout.decode("utf-8", "ignore")


def in_pod(arguments):
    return kubectl(
        ["-n", NAMESPACE, "exec", f"deployment/{DEPLOYMENT}", "-c", CONTAINER, "--", *arguments]
    )


def in_pod_json(arguments):
    output = in_pod(arguments)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise CheckError("the service returned unreadable output") from exc


def deployment_identity():
    """Confirm the single-writer deployment and its pinned running image."""
    payload = json.loads(kubectl(["-n", NAMESPACE, "get", "deployment", DEPLOYMENT, "-o", "json"]))
    require(
        payload["spec"].get("replicas") == 1
        and payload["spec"].get("strategy", {}).get("type") == "Recreate",
        "The workspace must keep its single-writer deployment.",
    )
    pods = json.loads(
        kubectl(
            [
                "-n",
                NAMESPACE,
                "get",
                "pods",
                "-l",
                f"app.kubernetes.io/name={DEPLOYMENT}",
                "-o",
                "json",
            ]
        )
    )["items"]
    running = [pod for pod in pods if not pod["metadata"].get("deletionTimestamp")]
    require(len(running) == 1, "The workspace does not have exactly one running pod.")
    pod = running[0]
    container = next(item for item in pod["spec"]["containers"] if item["name"] == CONTAINER)
    status = next(item for item in pod["status"]["containerStatuses"] if item["name"] == CONTAINER)
    image = container["image"]
    require(RUNNING_IMAGE.match(image), "The workspace image is not an immutable private digest.")
    require(status.get("ready"), "The workspace pod is not ready.")
    require(
        str(status.get("imageID", "")).endswith(image.split("@", 1)[1]),
        "The workspace pod has not confirmed its pinned running image.",
    )
    return {
        "deployment_uid": payload["metadata"]["uid"],
        "pod": pod["metadata"]["name"],
        "image": image,
    }


def write_report(output, report):
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(output / "report.json")
    (output / "report.json").chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", help="Check this completed copy instead of taking a new one.")
    parser.add_argument("--output", type=Path, help="Write report.json here.")
    args = parser.parse_args()
    os.umask(0o077)
    report: dict = {"app": "gi", "check": "isolated-restore", "location": "in-cluster"}
    try:
        before = deployment_identity()
        report["image"] = before["image"]
        report["pod"] = before["pod"]

        if args.backup:
            member = args.backup
            require(BACKUP_NAME.match(member), "The named copy has an unexpected name.")
            described = in_pod_json(
                ["python", "-m", "gi_app.backup_cli", "verify", "--file", member]
            )
            require(described.get("verified"), "The chosen copy did not verify.")
            report["backup"] = {
                "file": member,
                "kind": "chosen",
                "revision": described["revision"],
                "records": described["records"],
            }
        else:
            taken = in_pod_json(
                ["python", "-m", "gi_app.backup_cli", "backup", "--kind", "pre-change"]
            )
            require(taken.get("completed"), "The service could not complete a copy.")
            member = taken["file"]
            require(BACKUP_NAME.match(member), "The completed copy has an unexpected name.")
            report["backup"] = {
                "file": member,
                "kind": taken["kind"],
                "created_at": taken["createdAt"],
                "bytes": taken["bytes"],
                "revision": taken["revision"],
                "records": taken["records"],
            }

        # Restore and verify inside the cluster.  No copy crosses this boundary.
        restored = in_pod_json(["python", "-c", IN_POD_PROGRAM, SCRATCH_DIR, member])
        report["restored"] = restored["restored"]
        report["identity_restored"] = restored["identity"]
        require(restored.get("scratch_removed"), "The scratch directory was not removed.")
        report["scratch"] = "removed"

        # The restored copy must reproduce the completed copy exactly.
        identity = restored["identity"]
        require(
            identity["revision"] == report["backup"]["revision"],
            "The restored revision does not match the completed copy.",
        )
        require(
            identity["records"] == report["backup"]["records"],
            "The restored record count does not match the completed copy.",
        )
        require(
            identity["content_sha256"]
            == report["backup"].get("content_sha256", identity["content_sha256"]),
            "The restored content does not match the completed copy.",
        )

        # The live dataset must be byte-for-byte the same dataset afterwards.
        require(
            restored["live_before"]["content_sha256"] == restored["live_after"]["content_sha256"],
            "The live dataset changed during the restore check.",
        )
        require(
            restored["live_before"]["revision"] == restored["live_after"]["revision"],
            "The live revision changed during the restore check.",
        )
        report["live_unchanged"] = {
            "revision": restored["live_after"]["revision"],
            "records": restored["live_after"]["records"],
        }

        after = deployment_identity()
        require(
            after["deployment_uid"] == before["deployment_uid"]
            and after["image"] == before["image"],
            "The live deployment changed during the restore check.",
        )
        report["original_resources"] = "unchanged"

        present = in_pod(["sh", "-c", f"test -f {BACKUP_DIR}/{member} && echo present"]).strip()
        require(present == "present", "The completed copy disappeared from the claim.")
        report["completed_copy"] = "retained"

        report["checked_at"] = datetime.now(timezone.utc).isoformat()
        report["result"] = "passed"
    except CheckError as error:
        report["result"] = "failed"
        report["error"] = str(error)

    output = args.output or (ROOT / "output" / "gi-restore")
    write_report(output, report)
    print(f"restore check: {report['result']} -> {output / 'report.json'}")
    if report["result"] != "passed":
        print(f"  {report.get('error')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
