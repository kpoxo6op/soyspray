"""Exercise the paired backup with native images and disposable local containers."""

import json
import os
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTGRES = "postgres:16.10-bookworm@sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74"
RESTIC = (
    "restic/restic:0.18.1@sha256:39d9072fb5651c80d75c7a811612eb60b4c06b32ffe87c2e9f3c7222e1797e76"
)


def run(*args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=120, **kwargs)


class PairedBackup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "soyspray-backup-test-" + uuid.uuid4().hex[:10]
        subprocess.run(
            ["docker", "network", "create", cls.name], check=True, stdout=subprocess.DEVNULL
        )
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--rm",
                    "--name",
                    cls.name,
                    "--network",
                    cls.name,
                    "--network-alias",
                    "database",
                    "-e",
                    "POSTGRES_PASSWORD=isolated-fixture",
                    "-e",
                    "POSTGRES_DB=immich",
                    POSTGRES,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            for _ in range(60):
                if (
                    run(
                        "docker",
                        "exec",
                        cls.name,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-U",
                        "postgres",
                    ).returncode
                    == 0
                ):
                    return
                time.sleep(0.5)
            raise RuntimeError("The disposable PostgreSQL fixture did not start")
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        run("docker", "stop", cls.name)
        run("docker", "network", "rm", cls.name)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="soyspray-backup-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.scripts = ROOT / "backup"
        if image := os.environ.get("IMMICH_SCRIPT_IMAGE"):
            self.scripts = self.work / "scripts"
            self.scripts.mkdir()
            copied = run(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "-v",
                f"{self.scripts}:/work",
                image,
            )
            self.assertEqual(copied.returncode, 0, copied.stderr)
            for name in ("dump.sh", "dump.sql", "backup.sh"):
                self.assertEqual(
                    (self.scripts / name).read_bytes(), (ROOT / "backup" / name).read_bytes()
                )
        for name in (
            "backup",
            "repository",
            "restored",
            "media/upload",
            "media/library",
            "media/profile",
        ):
            (self.work / name).mkdir(parents=True)
        (self.work / "key").write_text("isolated-restic-fixture")
        self.relative = "upload/upload/photo with 'quotes'\nand Русский.jpg"
        self.photo = self.work / "media/upload" / self.relative.removeprefix("upload/upload/")
        self.photo.write_bytes(b"original fixture photo\0\xff")
        self.sql("""DROP SCHEMA public CASCADE; CREATE SCHEMA public;
          CREATE TABLE asset (id int PRIMARY KEY, "originalPath" text NOT NULL,
            "sidecarPath" text, "isExternal" boolean NOT NULL DEFAULT false);
          CREATE TABLE public."user" ("profileImagePath" text);
          CREATE TABLE album (id int PRIMARY KEY, title text);
          CREATE TABLE album_asset (album_id int REFERENCES album, asset_id int REFERENCES asset);
          INSERT INTO album VALUES (1, 'Isolated fixture album');""")
        escaped = self.relative.replace("'", "''")
        self.sql(
            f"INSERT INTO asset(id,\"originalPath\") VALUES(1,'{escaped}'); INSERT INTO album_asset VALUES(1,1);"
        )
        self.command(RESTIC, ["restic", "init"])

    def sql(self, statement, database="immich"):
        result = run(
            "docker",
            "exec",
            "--interactive",
            self.name,
            "psql",
            "-X",
            "-q",
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=on",
            "-U",
            "postgres",
            "-d",
            database,
            input=statement,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def arguments(self, image, command, extra=()):
        network = self.name if image == POSTGRES else "none"
        args = [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--read-only",
            "--tmpfs",
            "/tmp",
            "-v",
            f"{self.scripts}:/scripts:ro",
            "-v",
            f"{self.work / 'backup'}:/backup",
            "-v",
            f"{self.work / 'repository'}:/repository",
            "-v",
            f"{self.work / 'restored'}:/restored",
            "-v",
            f"{self.work / 'media'}:/usr/src/app/upload:ro",
            "-v",
            f"{self.work / 'key'}:/key:ro",
        ]
        for value in (
            "PGHOST=database",
            "PGUSER=postgres",
            "PGDATABASE=immich",
            "PGPASSWORD=isolated-fixture",
            "PGCONNECT_TIMEOUT=5",
            "RESTIC_REPOSITORY=/repository",
            "RESTIC_PASSWORD_FILE=/key",
            "RESTIC_CACHE_DIR=/backup/cache",
        ):
            args.extend(["-e", value])
        return args + list(extra) + ["--entrypoint", command[0], image, *command[1:]]

    def command(self, image, command, succeeds=True, extra=()):
        result = run(*self.arguments(image, command, extra))
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def dump(self, **kwargs):
        return self.command(POSTGRES, ["sh", "/scripts/dump.sh"], **kwargs)

    def backup(self, **kwargs):
        return self.command(RESTIC, ["sh", "/scripts/backup.sh"], **kwargs)

    def candidates(self):
        return json.loads(
            self.command(
                RESTIC, ["restic", "snapshots", "--json", "--tag", "restore-candidate"]
            ).stdout
        )

    def test_restore_preserves_files_database_and_album_membership(self):
        self.dump()
        self.backup()
        snapshots = self.candidates()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["hostname"], "immich")
        started = (self.work / "backup/database/started-at").read_text().strip().replace(
            " ", "T"
        ) + "Z"
        self.assertEqual(snapshots[0]["time"], started)
        self.command(
            RESTIC,
            ["restic", "restore", "latest", "--tag", "restore-candidate", "--target", "/restored"],
        )
        restored_photo = self.work / "restored/usr/src/app" / self.relative
        self.assertEqual(restored_photo.read_bytes(), self.photo.read_bytes())
        self.sql("DROP DATABASE IF EXISTS restored; CREATE DATABASE restored;", "postgres")
        self.command(
            POSTGRES,
            [
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "--dbname=restored",
                "/restored/backup/database/immich.dump",
            ],
        )
        self.assertEqual(
            self.sql(
                "SELECT count(*) FROM album JOIN album_asset ON album.id=album_id JOIN asset ON asset.id=asset_id;",
                "restored",
            ),
            "1",
        )

    def test_deletion_after_dump_never_becomes_a_candidate(self):
        self.dump()
        self.photo.unlink()
        self.backup(succeeds=False)
        self.assertEqual(self.candidates(), [])

    def test_move_after_dump_never_becomes_a_candidate(self):
        self.dump()
        self.photo.rename(self.photo.with_name("moved.jpg"))
        self.backup(succeeds=False)
        self.assertEqual(self.candidates(), [])

    def test_unreadable_source_never_becomes_a_candidate(self):
        self.dump()
        self.photo.chmod(0)
        self.addCleanup(self.photo.chmod, 0o600)
        self.backup(succeeds=False)
        self.assertEqual(self.candidates(), [])

    def test_database_connection_failure_stops_the_dump(self):
        self.dump(succeeds=False, extra=("-e", "PGDATABASE=does_not_exist"))
        self.assertEqual(self.candidates(), [])

    def test_external_library_requires_declared_mounts(self):
        self.sql('UPDATE asset SET "isExternal"=true;')
        self.dump(succeeds=False)
        self.assertEqual(self.candidates(), [])

    def test_dump_and_file_list_share_a_snapshot_during_concurrent_edits(self):
        wrapper = self.work / "bin"
        wrapper.mkdir()
        script = wrapper / "pg_dump"
        script.write_text("""#!/bin/sh
set -eu
touch /backup/exported
while ! test -f /backup/continue; do sleep 0.1; done
exec /usr/lib/postgresql/16/bin/pg_dump "$@"
""")
        script.chmod(0o755)
        args = self.arguments(
            POSTGRES,
            ["sh", "/scripts/dump.sh"],
            (
                "-v",
                f"{wrapper}:/testbin:ro",
                "-e",
                "PATH=/testbin:/usr/lib/postgresql/16/bin:/usr/bin:/bin",
            ),
        )
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(100):
                if (self.work / "backup/exported").exists():
                    break
                time.sleep(0.1)
            self.assertTrue((self.work / "backup/exported").exists())
            self.sql("DELETE FROM album_asset; DELETE FROM asset;")
        finally:
            (self.work / "backup/continue").touch()
            stdout, stderr = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 0, stderr + stdout)
        self.backup()
        self.sql(
            "DROP DATABASE IF EXISTS snapshot_test; CREATE DATABASE snapshot_test;", "postgres"
        )
        self.command(
            POSTGRES,
            [
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "--dbname=snapshot_test",
                "/backup/database/immich.dump",
            ],
        )
        self.assertEqual(self.sql("SELECT count(*) FROM asset;", "snapshot_test"), "1")
        paths = (self.work / "backup/database/required-files.raw").read_bytes().split(b"\0")
        self.assertIn(("/usr/src/app/" + self.relative).encode(), paths)


if __name__ == "__main__":
    unittest.main(verbosity=2)
