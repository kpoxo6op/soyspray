#!/usr/bin/env python3
"""Back up the proven node-local recovery inputs with Restic."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

JELLYFIN_DIRS = ("data", "metadata", "plugins", "root")
REQUIRED_ENV = (
    "RESTIC_REPOSITORY",
    "RESTIC_PASSWORD_FILE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
)
EXCLUDED_DATABASE_FILES = {"jellyfin.db", "jellyfin.db-wal", "jellyfin.db-shm"}


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_report(root: Path, logical_root: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        logical_path = f"{logical_root}/{path.relative_to(root).as_posix()}"
        if path.is_symlink():
            entries.append(
                {"path": logical_path, "type": "symlink", "target": os.readlink(path)}
            )
        elif path.is_file():
            entries.append(
                {
                    "path": logical_path,
                    "type": "file",
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    return entries


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"required directory is missing: {source}")
    shutil.copytree(
        source,
        destination,
        symlinks=True,
        ignore=lambda _path, names: EXCLUDED_DATABASE_FILES.intersection(names),
    )


def _snapshot_sqlite(source_path: Path, destination_path: Path) -> dict[str, Any]:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True, timeout=30)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination, pages=256, sleep=0.05)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise RuntimeError(f"SQLite integrity check failed: {integrity!r}")
        destination.commit()
    finally:
        destination.close()
        source.close()
    return {
        "source": "live/jellyfin/data/jellyfin.db",
        "shadow": "staged/jellyfin/data/jellyfin.db",
        "integrity_check": "ok",
        "bytes": destination_path.stat().st_size,
        "sha256": _sha256(destination_path),
    }


def _restic_json_lines(output: str) -> Iterable[dict[str, Any]]:
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            yield value
        elif isinstance(value, list):
            yield from (item for item in value if isinstance(item, dict))


def _run_restic(args: list[str], environment: dict[str, str]) -> str:
    result = subprocess.run(
        ["restic", *args],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30 * 60,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"restic {args[0]} failed with exit code {result.returncode}")
    return result.stdout


def _validate_saved_tree(output: str, snapshot_id: str) -> list[str]:
    paths = [
        str(item["path"])
        for item in _restic_json_lines(output)
        if item.get("struct_type") == "node" and isinstance(item.get("path"), str)
    ]
    for required in (
        "jellyfin/data/jellyfin.db",
        "jellyfin/metadata",
        "jellyfin/plugins",
        "jellyfin/root",
        "books",
    ):
        if not any(path.endswith(required) for path in paths):
            raise RuntimeError(f"Restic snapshot {snapshot_id} is missing {required}")
    for path in paths:
        name = PurePosixPath(path).name
        if name in {"jellyfin.db-wal", "jellyfin.db-shm"}:
            raise RuntimeError(f"Restic snapshot {snapshot_id} contains excluded file {name}")
    database_paths = [path for path in paths if PurePosixPath(path).name == "jellyfin.db"]
    if len(database_paths) != 1:
        raise RuntimeError(
            f"Restic snapshot {snapshot_id} contains {len(database_paths)} Jellyfin databases"
        )
    return sorted(paths)


def _required_inputs(environment: dict[str, str]) -> None:
    missing = [name for name in REQUIRED_ENV if not environment.get(name)]
    if missing:
        raise RuntimeError(f"missing recovery inputs: {', '.join(missing)}")
    password_file = Path(environment["RESTIC_PASSWORD_FILE"])
    if not password_file.is_file():
        raise RuntimeError("RESTIC_PASSWORD_FILE does not point to a file")


def run() -> int:
    environment = os.environ.copy()
    work = Path(environment.get("BACKUP_WORKDIR", "/work"))
    report_path = work / "reports" / "report.json"
    report: dict[str, Any] = {
        "schema": "soyspray.node-backup/v1",
        "run_id": uuid.uuid4().hex,
        "result": "failed",
        "inputs": {
            "jellyfin_directories": list(JELLYFIN_DIRS),
            "books": "downloads/books",
            "excluded_database_files": sorted(EXCLUDED_DATABASE_FILES),
        },
        "files": [],
    }
    try:
        _required_inputs(environment)
        jellyfin_source = Path(environment.get("JELLYFIN_SOURCE", "/source/jellyfin"))
        downloads_source = Path(environment.get("DOWNLOADS_SOURCE", "/source/downloads"))
        database_source = jellyfin_source / "data" / "jellyfin.db"
        if not database_source.is_file():
            raise FileNotFoundError(f"required database is missing: {database_source}")
        books_source = downloads_source / "books"
        if not books_source.is_dir():
            raise FileNotFoundError(f"required directory is missing: {books_source}")

        work.mkdir(parents=True, exist_ok=True)
        environment.setdefault("AWS_DEFAULT_REGION", environment["AWS_REGION"])
        environment.setdefault("RESTIC_CACHE_DIR", str(work / "cache"))
        with tempfile.TemporaryDirectory(prefix="node-backup-", dir=work) as temporary:
            stage = Path(temporary)
            stage_jellyfin = stage / "jellyfin"
            stage_books = stage / "books"
            stage_jellyfin.mkdir()
            for directory in JELLYFIN_DIRS:
                _copy_tree(jellyfin_source / directory, stage_jellyfin / directory)
            report["sqlite"] = _snapshot_sqlite(
                database_source, stage_jellyfin / "data" / "jellyfin.db"
            )
            _copy_tree(books_source, stage_books)
            report["files"] = _file_report(stage_jellyfin, "jellyfin") + _file_report(
                stage_books, "books"
            )
            backup_output = _run_restic(
                [
                    "backup",
                    "--retry-lock",
                    "5m",
                    "--json",
                    "--host",
                    environment.get("RESTIC_HOST", "soyspray-node-0"),
                    "--group-by",
                    "host",
                    "--tag",
                    "node-local",
                    str(stage_jellyfin),
                    str(stage_books),
                ],
                environment,
            )
            summaries = [
                item
                for item in _restic_json_lines(backup_output)
                if item.get("message_type") == "summary"
            ]
            if len(summaries) != 1 or not isinstance(summaries[0].get("snapshot_id"), str):
                raise RuntimeError("Restic backup returned no valid snapshot summary")
            snapshot_id = summaries[0]["snapshot_id"]
            if len(snapshot_id) != 64 or any(char not in "0123456789abcdef" for char in snapshot_id):
                raise RuntimeError("Restic backup returned an invalid snapshot id")
            saved_paths = _validate_saved_tree(
                _run_restic(["ls", "--json", snapshot_id], environment), snapshot_id
            )
            report["snapshot"] = {"id": snapshot_id, "saved_paths": saved_paths}
            report["result"] = "passed"
    except Exception as error:  # The report must survive every ordinary failure.
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    _write_report(report_path, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(run())
