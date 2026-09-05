"""Check an idle restored vault and decrypt only its restricted recovery record."""

import json
import os
import re
import sqlite3
import ssl
import subprocess
import time
import urllib.request
from contextlib import closing

from apps.vaultwarden.agent_secret import ITEM_NAME
from scripts.restore_common import require


def check_data(directory):
    # The inspector has no database writer. Copy the full directory, including WAL,
    # before starting the stock server; then use SQLite's backup API locally.
    require(
        not any(path.is_symlink() for path in directory.rglob("*")),
        "The restored data contains a symlink; file checks stopped.",
    )
    database = directory / "db.sqlite3"
    require(database.is_file(), "The restored SQLite database is missing.")
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(":memory:")) as checked:
            source.backup(checked)
            require(
                checked.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                "Restored SQLite integrity failed.",
            )
            require(
                not checked.execute("PRAGMA foreign_key_check").fetchall(),
                "Restored SQLite foreign keys failed.",
            )
            counts = {
                table: checked.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                for table in ("users", "ciphers", "attachments")
            }
            attachments = checked.execute(
                "SELECT id, cipher_uuid, file_size FROM attachments"
            ).fetchall()
            for attachment, cipher, expected_size in attachments:
                require(
                    all(
                        isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9-]+", value)
                        for value in (attachment, cipher)
                    ),
                    "A restored attachment has an invalid storage path.",
                )
                path = directory / "attachments" / cipher / attachment
                require(
                    path.is_file()
                    and path.stat().st_size > 0
                    and path.stat().st_size == expected_size,
                    "A recorded encrypted attachment is missing, empty, or has the wrong size.",
                )
                require(
                    checked.execute("SELECT 1 FROM ciphers WHERE uuid = ?", (cipher,)).fetchone(),
                    "A restored attachment has no parent record.",
                )
    require((directory / "rsa_key.pem").is_file(), "The restored server signing key is missing.")
    return {
        "sqlite_integrity": "ok",
        "foreign_keys": "ok",
        "users": counts["users"],
        "encrypted_records": counts["ciphers"],
        "encrypted_attachments": counts["attachments"],
        "attachment_files": {"value": "present"}
        if attachments
        else {"value": "unknown", "cause": "This snapshot contains no attachment records."},
        "human_unlock": {"value": "unknown", "cause": "The human master password was not used."},
        "attachment_decryption": {
            "value": "unknown",
            "cause": "Only stored encrypted attachment files were checked.",
        },
    }


def check_login(namespace, work, kube_env, inputs):
    certificate = work / "tls/cert.pem"
    cli = work / "restricted-cli"
    cli.mkdir(mode=0o700)
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(cli),
        "BITWARDENCLI_APPDATA_DIR": str(cli),
        "NODE_EXTRA_CA_CERTS": str(certificate),
        "BW_RESTORE_PASSWORD": inputs["password"],
    }

    def bw(*args):
        completed = subprocess.run(
            ["bw", *args, "--nointeraction"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
        )
        # Never copy CLI output, decrypted data, or errors into operator reports.
        require(completed.returncode == 0, "The isolated restricted CLI operation failed.")
        return completed.stdout.strip()

    with (work / "port-forward.log").open("w") as log:
        forward = subprocess.Popen(
            [
                "kubectl",
                "-n",
                namespace,
                "port-forward",
                "--address=127.0.0.1",
                "pod/app",
                "18443:8443",
            ],
            env=kube_env,
            stdout=log,
            stderr=log,
        )
        try:
            client = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                urllib.request.HTTPSHandler(
                    context=ssl.create_default_context(cafile=str(certificate))
                ),
            )
            for _ in range(50):
                require(forward.poll() is None, "The isolated port forward stopped.")
                try:
                    with client.open("https://localhost:18443/alive", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise ValueError("The isolated TLS endpoint did not become ready.")
            bw("config", "server", "https://localhost:18443", "--quiet")
            session = bw("login", inputs["email"], "--passwordenv", "BW_RESTORE_PASSWORD", "--raw")
            require(session, "The restored restricted login returned no session.")
            environment.pop("BW_RESTORE_PASSWORD", None)
            environment["BW_SESSION"] = session
            bw("sync", "--quiet")
            item = json.loads(bw("get", "item", ITEM_NAME))
            require(
                item.get("name") == ITEM_NAME
                and all(
                    isinstance(item.get("login", {}).get(key), str) and item["login"][key]
                    for key in ("username", "password")
                ),
                "The restored restricted record did not decrypt into the expected login fields.",
            )
            return {"restricted_agent_login": True, "restricted_record_decryption": True}
        finally:
            environment.pop("BW_RESTORE_PASSWORD", None)
            try:
                if environment.get("BW_SESSION"):
                    bw("lock", "--quiet")
            finally:
                environment.pop("BW_SESSION", None)
                forward.terminate()
                try:
                    forward.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    forward.kill()
                    forward.wait(timeout=10)
