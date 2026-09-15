#!/usr/bin/env python3
"""Restore a completed private workspace copy into isolation and check it.

The workspace owns its copies, so this check does not use a Longhorn backup.
It asks the running application to take and describe a completed copy, reads
only that copy out of the namespace, restores it into a scratch directory on
this machine, and verifies the restored database with an independent SQLite
reader that shares no code with the application.  Finally it confirms that the
live service is exactly where it started.

Output is counts, sizes, identifiers, and ages only.  No stored value is read,
printed, or written, and the scratch directory is removed unless it is asked
for.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = "gi"
DEPLOYMENT = "gi"
CONTAINER = "web"
BACKUP_DIR = "/backups"
RUNNING_IMAGE = re.compile(r"^ghcr\.io/kpoxo6op/gi-app@sha256:[0-9a-f]{64}$")
BACKUP_NAME = re.compile(r"^gi-(daily|pre-change)-\d{8}T\d{6}Z-[0-9a-f]{12}\.sqlite3$")


class CheckError(Exception):
    """The check could not continue, or a required condition failed."""


def require(value, cause):
    if not value:
        raise CheckError(cause)


def kubectl(arguments, *, binary=False):
    try:
        result = subprocess.run(["kubectl", *arguments], capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CheckError(f"kubectl could not run: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "ignore").strip()[:200]
        raise CheckError(f"kubectl {' '.join(arguments[:3])} failed: {detail}")
    return result.stdout if binary else result.stdout.decode("utf-8", "ignore")


def in_pod(script_arguments, *, binary=False):
    """Run one command inside the running pod."""
    return kubectl(
        [
            "-n",
            NAMESPACE,
            "exec",
            f"deployment/{DEPLOYMENT}",
            "-c",
            CONTAINER,
            "--",
            *script_arguments,
        ],
        binary=binary,
    )


def in_pod_json(script_arguments):
    output = in_pod(script_arguments)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise CheckError("the application returned unreadable output") from exc


def live_counts():
    """Read the live dataset summary through the application's own API."""
    payload = in_pod_json(
        [
            "python",
            "-c",
            "import json,urllib.request as u;"
            "d=json.load(u.urlopen('http://127.0.0.1:8080/api/dataset'))['dataset'];"
            "print(json.dumps({'revision':d.get('revision'),'records':len(d.get('records') or [])}))",
        ]
    )
    require(isinstance(payload.get("revision"), int), "The live dataset has no revision.")
    return payload


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


def stream_copy(member, scratch):
    """Read one completed copy out of the pod and write it to scratch."""
    archive = in_pod(["tar", "-C", BACKUP_DIR, "-cf", "-", member], binary=True)
    require(len(archive) > 0, "The streamed copy was empty.")
    archive_path = scratch / "copy.tar"
    archive_path.write_bytes(archive)
    try:
        with tarfile.open(archive_path) as bundle:
            # The archive may or may not carry a directory prefix, so match on
            # the file name rather than assuming a path.
            found = [item for item in bundle.getmembers() if Path(item.name).name == member]
            require(found and found[0].isfile(), "The streamed archive did not contain the copy.")
            handle = bundle.extractfile(found[0])
            require(handle is not None, "The streamed copy could not be read.")
            target = scratch / member
            target.write_bytes(handle.read())
    except tarfile.TarError as exc:
        raise CheckError("The streamed copy was not a readable archive.") from exc
    except KeyError as exc:
        raise CheckError("The streamed archive did not contain the copy.") from exc
    finally:
        archive_path.unlink(missing_ok=True)
    return target, hashlib.sha256(archive).hexdigest()


def restore_without_the_application(source, target):
    """Restore the copy with a plain SQLite reader.

    This shares no code with the application, so a pass means the copy itself is
    restorable rather than that the application agrees with itself.
    """
    origin = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        restored = sqlite3.connect(target)
        try:
            origin.backup(restored)
        finally:
            restored.close()
    finally:
        origin.close()
    return target


def verify_restored(path, expected):
    """Read a restored copy independently and compare it with the copy."""
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise CheckError("The restored copy could not be opened.") from exc
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        require(integrity and integrity[0] == "ok", "The restored copy failed its integrity check.")
        row = connection.execute("SELECT content FROM gi_dataset WHERE id = 1").fetchone()
        require(row is not None, "The restored copy has no dataset row.")
        try:
            dataset = json.loads(row[0])
        except (TypeError, ValueError) as exc:
            raise CheckError("The restored copy has an unreadable dataset.") from exc
        require(
            dataset.get("revision") == expected["revision"],
            "The restored revision does not match the completed copy.",
        )
        records = dataset.get("records")
        require(isinstance(records, list), "The restored copy has no record list.")
        require(
            len(records) == expected["records"],
            "The restored record count does not match the completed copy.",
        )
        empty_history = [
            record.get("id")
            for record in records
            if not isinstance(record.get("revisions"), list) or not record["revisions"]
        ]
        require(not empty_history, "A restored record lost its revision history.")
        return {
            "revision": dataset["revision"],
            "records": len(records),
            "sources": len(dataset.get("sources") or []),
            "plan_versions": len(dataset.get("planVersions") or []),
            "events": len(dataset.get("events") or []),
            "milestone_states": len(dataset.get("milestoneStates") or []),
        }
    finally:
        connection.close()


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
    parser.add_argument(
        "--keep-scratch", action="store_true", help="Keep the restored database for inspection."
    )
    args = parser.parse_args()
    os.umask(0o077)
    report: dict = {"app": "gi", "check": "isolated-restore"}
    scratch = Path(tempfile.mkdtemp(prefix="gi-restore-check-"))
    try:
        before_identity = deployment_identity()
        report["image"] = before_identity["image"]
        report["pod"] = before_identity["pod"]
        before_live = live_counts()
        report["live_before"] = before_live

        if args.backup:
            member = args.backup
            taken = in_pod_json(["python", "-m", "gi_app.backup_cli", "verify", "--file", member])
            require(taken.get("verified"), "The chosen copy did not verify.")
            report["backup"] = {
                "file": member,
                "kind": "chosen",
                "revision": taken["revision"],
                "records": taken["records"],
            }
        else:
            taken = in_pod_json(
                ["python", "-m", "gi_app.backup_cli", "backup", "--kind", "pre-change"]
            )
            require(taken.get("completed"), "The application could not complete a copy.")
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

        local_copy, archive_digest = stream_copy(member, scratch)
        report["stream_sha256"] = archive_digest
        report["stream_bytes"] = local_copy.stat().st_size

        restored_path = scratch / "restored.sqlite3"
        restore_without_the_application(local_copy, restored_path)
        report["restored"] = verify_restored(restored_path, report["backup"])

        after_live = live_counts()
        report["live_after"] = after_live
        require(
            after_live["revision"] == before_live["revision"],
            "The live revision changed during the restore check.",
        )
        require(
            after_live["records"] == before_live["records"],
            "The live record count changed during the restore check.",
        )
        after_identity = deployment_identity()
        require(
            after_identity["deployment_uid"] == before_identity["deployment_uid"]
            and after_identity["image"] == before_identity["image"],
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
    finally:
        if args.keep_scratch:
            report["scratch"] = str(scratch)
        else:
            shutil.rmtree(scratch, ignore_errors=True)

    output = args.output or (ROOT / "output" / "gi-restore")
    write_report(output, report)
    print(f"restore check: {report['result']} -> {output / 'report.json'}")
    if report["result"] != "passed":
        print(f"  {report.get('error')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
