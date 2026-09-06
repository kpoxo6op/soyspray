"""Test the node-local Restic package with SQLite and a local Restic repository."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backup.py"


class NodeBackup(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="soyspray-node-backup-")
        self.root = Path(self.temp.name)
        self.jellyfin = self.root / "jellyfin"
        self.downloads = self.root / "downloads"
        for name in ("data", "metadata", "plugins", "root"):
            (self.jellyfin / name).mkdir(parents=True)
        (self.downloads / "books").mkdir(parents=True)
        (self.jellyfin / "metadata" / "library.json").write_text("metadata")
        (self.jellyfin / "plugins" / "plugin.json").write_text("plugin")
        (self.jellyfin / "root" / "system.xml").write_text("root")
        (self.downloads / "books" / "book.epub").write_bytes(b"book")
        self.database = self.jellyfin / "data" / "jellyfin.db"
        with sqlite3.connect(self.database) as database:
            database.execute("CREATE TABLE item(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            database.executemany("INSERT INTO item(value) VALUES (?)", [(f"item-{n}",) for n in range(1000)])
        # These files must never be collected with the shadow database.
        (self.jellyfin / "data" / "jellyfin.db-wal").write_bytes(b"original wal")
        (self.jellyfin / "data" / "jellyfin.db-shm").write_bytes(b"original shm")
        self.key = self.root / "password"
        self.key.write_text("isolated-node-backup-test")
        self.work = self.root / "work"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def environment(self, repository: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "BACKUP_WORKDIR": str(self.work),
                "JELLYFIN_SOURCE": str(self.jellyfin),
                "DOWNLOADS_SOURCE": str(self.downloads),
                "RESTIC_REPOSITORY": str(repository),
                "RESTIC_PASSWORD_FILE": str(self.key),
                "AWS_ACCESS_KEY_ID": "isolated-access-key",
                "AWS_SECRET_ACCESS_KEY": "isolated-secret-key",
                "AWS_REGION": "us-east-1",
            }
        )
        return environment

    def install_fake_success_restic(self) -> None:
        fake_restic = self.root / "restic"
        fake_restic.write_text(
            """#!/usr/bin/env python3
import json, sys
if sys.argv[1] == "backup":
    print(json.dumps({"message_type": "summary", "snapshot_id": "a" * 64}))
elif sys.argv[1] == "ls":
    for path in (
        "/temporary/jellyfin/data/jellyfin.db",
        "/temporary/jellyfin/metadata",
        "/temporary/jellyfin/plugins",
        "/temporary/jellyfin/root",
        "/temporary/books",
    ):
        print(json.dumps({"struct_type": "node", "type": "file", "path": path}))
else:
    raise SystemExit(2)
"""
        )
        fake_restic.chmod(0o755)

    def run_backup(self, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def report(self) -> dict:
        return json.loads((self.work / "reports" / "report.json").read_text())

    def test_concurrent_writer_creates_integrity_checked_shadow(self) -> None:
        repository = self.root / "repository"
        writer_started = threading.Event()
        stop_writer = threading.Event()

        def writer() -> None:
            with sqlite3.connect(self.database, timeout=30) as database:
                database.execute("PRAGMA journal_mode=WAL")
                writer_started.set()
                for n in range(2000):
                    database.execute("UPDATE item SET value=? WHERE id=?", (f"changed-{n}", n % 1000 + 1))
                    database.commit()
                    if stop_writer.is_set():
                        break
                    time.sleep(0.001)

        with sqlite3.connect(self.database) as database:
            database.execute("PRAGMA journal_mode=WAL")
        repository = self.root / "repository"
        environment = self.environment(repository)
        if shutil.which("restic"):
            subprocess.run(
                ["restic", "init"],
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        else:
            self.install_fake_success_restic()
            environment["PATH"] = f"{self.root}:{environment['PATH']}"
        thread = threading.Thread(target=writer)
        thread.start()
        self.assertTrue(writer_started.wait(10))
        try:
            result = self.run_backup(environment)
        finally:
            stop_writer.set()
            thread.join(timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = self.report()
        self.assertEqual((self.work / "reports" / "report.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(report["result"], "passed")
        self.assertEqual(report["sqlite"]["integrity_check"], "ok")
        self.assertEqual(
            [entry["path"] for entry in report["files"] if entry["path"].endswith("jellyfin.db")],
            ["jellyfin/data/jellyfin.db"],
        )
        saved_paths = report["snapshot"]["saved_paths"]
        self.assertTrue(any(path.endswith("jellyfin/data/jellyfin.db") for path in saved_paths))
        self.assertFalse(any(path.endswith("jellyfin.db-wal") for path in saved_paths))
        self.assertFalse(any(path.endswith("jellyfin.db-shm") for path in saved_paths))

    def test_restic_failure_keeps_a_failed_report(self) -> None:
        fake_restic = self.root / "restic"
        fake_restic.write_text("#!/bin/sh\nexit 23\n")
        fake_restic.chmod(0o755)
        environment = self.environment(self.root / "repository")
        environment["PATH"] = f"{self.root}:{environment['PATH']}"
        result = self.run_backup(environment)
        self.assertNotEqual(result.returncode, 0)
        report = self.report()
        self.assertEqual((self.work / "reports" / "report.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(report["result"], "failed")
        self.assertEqual(report["error"]["type"], "RuntimeError")
        self.assertNotIn("isolated-secret-key", json.dumps(report))

    @unittest.skipUnless(shutil.which("restic"), "restic is not installed")
    def test_local_restic_restore(self) -> None:
        repository = self.root / "repository"
        subprocess.run(
            ["restic", "init"],
            env=self.environment(repository),
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        result = self.run_backup(self.environment(repository))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        restored = self.root / "restored"
        subprocess.run(
            ["restic", "restore", "latest", "--target", str(restored)],
            env=self.environment(repository),
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        restored_databases = list(restored.rglob("jellyfin.db"))
        self.assertEqual(len(restored_databases), 1)
        with sqlite3.connect(restored_databases[0]) as database:
            self.assertEqual(database.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        self.assertFalse(list(restored.rglob("jellyfin.db-wal")))
        self.assertFalse(list(restored.rglob("jellyfin.db-shm")))


if __name__ == "__main__":
    unittest.main()
