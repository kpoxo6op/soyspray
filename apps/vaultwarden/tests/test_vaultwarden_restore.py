import base64
import copy
import sqlite3
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

from apps.vaultwarden.check_restore import check_data
from apps.vaultwarden.restore_check import runtime_values

ROOT = Path(__file__).resolve().parents[3]


def database(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    connection = sqlite3.connect(directory / "db.sqlite3")
    connection.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA wal_autocheckpoint=0;
        CREATE TABLE users (uuid TEXT PRIMARY KEY);
        CREATE TABLE ciphers (uuid TEXT PRIMARY KEY);
        CREATE TABLE attachments (id TEXT PRIMARY KEY, cipher_uuid TEXT REFERENCES ciphers(uuid), file_size INTEGER);
        INSERT INTO users VALUES ('user-1');
        INSERT INTO ciphers VALUES ('cipher-1');
        INSERT INTO attachments VALUES ('attachment-1', 'cipher-1', 20);
    """)
    connection.commit()
    path = directory / "attachments/cipher-1/attachment-1"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"encrypted-attachment")
    (directory / "rsa_key.pem").write_text("synthetic-key")
    return directory, connection, path


def test_snapshot_includes_wal_and_reports_only_counts_and_limits(tmp_path):
    directory, writer, path = database(tmp_path)
    try:
        assert (directory / "db.sqlite3-wal").stat().st_size > 0
        result = check_data(directory)
        assert (
            result["users"] == result["encrypted_records"] == result["encrypted_attachments"] == 1
        )
        assert result["sqlite_integrity"] == "ok"
        assert (
            result["human_unlock"]["value"] == result["attachment_decryption"]["value"] == "unknown"
        )
        writer.execute("DELETE FROM attachments")
        writer.commit()
        assert check_data(directory)["attachment_files"]["value"] == "unknown"
    finally:
        writer.close()


@pytest.mark.parametrize(
    "failure", ["missing", "empty", "truncated", "symlink", "traversal", "orphan", "key", "corrupt"]
)
def test_broken_data_cannot_pass(tmp_path, failure):
    directory, writer, path = database(tmp_path)
    if failure == "missing":
        path.unlink()
    elif failure == "empty":
        path.write_bytes(b"")
    elif failure == "truncated":
        path.write_bytes(b"short")
    elif failure == "symlink":
        path.unlink()
        path.symlink_to(directory / "rsa_key.pem")
    elif failure == "traversal":
        writer.execute("UPDATE attachments SET id = '../../outside'")
    elif failure == "orphan":
        writer.execute("DELETE FROM ciphers")
    elif failure == "key":
        (directory / "rsa_key.pem").unlink()
    writer.commit()
    writer.close()
    if failure == "corrupt":
        (directory / "db.sqlite3").write_bytes(b"not sqlite")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        check_data(directory)


def test_only_archived_original_restricted_identity_is_accepted():
    archive = {
        "vaultwarden_agent_email": "automation@vault.soyspray.vip",
        "vaultwarden_agent_master_password": "synthetic-password",
    }
    secret = {
        "data": {
            "email": base64.b64encode(archive["vaultwarden_agent_email"].encode()).decode(),
            "master-password": base64.b64encode(b"synthetic-password").decode(),
        }
    }
    assert runtime_values(archive, secret)["password"] == "synthetic-password"
    for changes in (
        {"vaultwarden_agent_email": "human@example.test"},
        {"vaultwarden_agent_master_password": "different"},
        {"vaultwarden_agent_master_password": None},
    ):
        with pytest.raises(ValueError):
            runtime_values({**archive, **changes}, secret)


@pytest.mark.parametrize(
    "image,accepted",
    [
        ("ghcr.io/dani-garcia/vaultwarden:testing@sha256:" + "a" * 64, True),
        ("ghcr.io/dani-garcia/vaultwarden:1.0@sha256:" + "b" * 64, True),
        ("ghcr.io/dani-garcia/vaultwarden@sha256:" + "b" * 64, True),
        ("ghcr.io/dani-garcia/vaultwarden:latest", False),
        ("ghcrXio/dani-garcia/vaultwarden@sha256:" + "a" * 64, False),
        ("ghcr.io/other/vaultwarden@sha256:" + "a" * 64, False),
        ("", False),
    ],
)
def test_native_restore_accepts_only_pinned_stock_images(image, accepted):
    tasks = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/start-restored-app.yml").read_text()
    )[0]["tasks"]
    guard = next(
        condition
        for task in tasks
        for condition in task.get("ansible.builtin.assert", {}).get("that", [])
        if "recovery_vaultwarden_image" in condition
    )
    variables = {"recovery_vaultwarden_image": image}
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = [guard]
    assert (
        condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
        is accepted
    )


@pytest.mark.parametrize(
    "failure",
    [None, "preflight", "restore", "interrupt", "data", "start", "login", "original", "cleanup"],
)
def test_restore_operation_cleans_up_after_failures_and_never_reports_partial_success(
    tmp_path, monkeypatch, capsys, failure
):
    import json
    import os
    import subprocess
    import sys

    from apps.vaultwarden import restore_check
    from scripts import restore_common

    root = tmp_path / "checkout"
    root.mkdir()
    vault = tmp_path / "runtime.vault.yml"
    vault.write_text("$ANSIBLE_VAULT;synthetic")
    password = tmp_path / "password"
    password.write_text("synthetic")
    monkeypatch.setattr(restore_check, "ROOT", root)
    monkeypatch.setattr(
        sys,
        "argv",
        ["restore-check", "--vault-file", str(vault), "--vault-password-file", str(password)],
    )
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    image = "ghcr.io/dani-garcia/vaultwarden@sha256:" + "a" * 64
    claim = {
        "metadata": {"uid": "claim-uid"},
        "spec": {"volumeName": "pvc-original", "storageClassName": "longhorn"},
        "status": {"phase": "Bound"},
    }
    volume = {
        "metadata": {"uid": "volume-uid"},
        "spec": {
            "claimRef": {"uid": "claim-uid"},
            "csi": {"driver": "driver.longhorn.io", "volumeHandle": "pvc-original"},
        },
    }
    deployment = {
        "metadata": {"uid": "deployment-uid"},
        "spec": {"replicas": 1, "strategy": {"type": "Recreate"}},
    }
    secret = {
        "metadata": {"uid": "secret-uid"},
        "data": {
            "email": base64.b64encode(b"automation@vault.soyspray.vip").decode(),
            "master-password": base64.b64encode(b"synthetic-identity-with-no-live-access").decode(),
        },
    }
    pod = {
        "metadata": {"name": "vaultwarden"},
        "spec": {"containers": [{"name": "vaultwarden", "image": image}]},
        "status": {"containerStatuses": [{"name": "vaultwarden", "imageID": image, "ready": True}]},
    }
    operations = []
    volume_reads = 0

    def read(args, **kwargs):
        nonlocal volume_reads
        if args[:2] == ["git", "rev-parse"]:
            return "source-commit\n"
        if "view" in args:
            value = (
                {"contexts": []}
                if args[0] == "kubectl"
                else {
                    "vaultwarden_agent_email": "automation@vault.soyspray.vip",
                    "vaultwarden_agent_master_password": "synthetic-identity-with-no-live-access",
                }
            )
        else:
            config = Path(kwargs["env"]["KUBECONFIG"])
            assert config.stat().st_mode & 0o777 == 0o600
            if "pvc" in args:
                value = (
                    {"metadata": {"uid": "restored-uid"}, "spec": {"volumeName": "isolated"}}
                    if "restored-data" in args
                    else claim
                )
            elif "pv" in args:
                volume_reads += 1
                value = copy.deepcopy(volume)
                if failure == "original" and volume_reads > 1:
                    value["metadata"]["uid"] = "replacement"
            elif "backups.longhorn.io" in args:
                value = {
                    "items": [
                        {
                            "metadata": {"name": "backup", "uid": "backup-uid"},
                            "status": {
                                "volumeName": "pvc-original",
                                "backupTargetName": "critical-s3",
                                "state": "Completed",
                                "progress": 100,
                                "snapshotCreatedAt": "2020-01-01T00:00:00Z",
                                "url": "s3://example/backup",
                            },
                        }
                    ]
                }
            elif "secret" in args:
                value = secret
            elif "deployment" in args:
                value = deployment
            elif "pods" in args:
                value = {"items": [pod]}
            else:
                raise AssertionError(args)
        return json.dumps(value).encode()

    def run(args, **kwargs):
        if args[0] == "make":
            assert args == ["make", "go"]
            if failure == "preflight":
                raise subprocess.CalledProcessError(2, args)
        elif str(args[0]).endswith("ansible-playbook"):
            assert Path(kwargs["env"]["KUBECONFIG"]).is_file()
            assert args[-1].startswith("@")
            private = Path(args[-1][1:])
            assert private.stat().st_mode & 0o777 == 0o600
            variables = json.loads(private.read_text())
            assert variables["recovery_expected_claim_uid"] == "claim-uid"
            assert variables["recovery_expected_backup_uid"] == "backup-uid"
            action = (
                "cleanup"
                if "cleanup-restore.yml" in args[-3]
                else "start"
                if "start-restored-app.yml" in args[-3]
                else "restore"
            )
            operations.append(action)
            if failure == "interrupt" and action == "restore":
                raise KeyboardInterrupt
            if failure == action:
                raise subprocess.CalledProcessError(2, args)
        elif args[0] == "openssl":
            pass
        else:
            assert args[:2] == ["kubectl", "cp"]
        return subprocess.CompletedProcess(args, 0)

    def data(path):
        if failure == "data":
            raise ValueError("Synthetic invalid data")
        return {"sqlite_integrity": "ok"}

    def login(*args):
        if failure == "login":
            raise ValueError("Synthetic failed login")
        return {"restricted_agent_login": True}

    monkeypatch.setattr(restore_check, "check_data", data)
    monkeypatch.setattr(restore_check, "check_login", login)
    monkeypatch.setattr(restore_common, "capture_output", read)
    monkeypatch.setattr(restore_common, "run_process", run)
    old_umask = os.umask(0o077)
    try:
        code = restore_check.main()
    finally:
        os.umask(old_umask)
    reports = list((tmp_path / "state").rglob("report.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text())
    assert reports[0].stat().st_mode & 0o777 == 0o600
    assert report["status"] == ("failed" if failure else "passed")
    assert code == (2 if failure else 0)
    assert operations == (
        []
        if failure == "preflight"
        else ["restore", "cleanup"]
        if failure in {"restore", "interrupt", "data"}
        else ["restore", "start", "cleanup"]
    )
    assert report["cleanup"] == (
        "not started"
        if failure == "preflight"
        else "failed - inspect the guarded cleanup log"
        if failure == "cleanup"
        else "completed"
    )
    assert not list(reports[0].parent.glob("working-*"))
    assert "synthetic-identity-with-no-live-access" not in capsys.readouterr().out


@pytest.mark.parametrize("failure", [None, "forward", "login", "record", "lock"])
def test_restricted_login_uses_private_cli_state_and_always_stops_forward(
    tmp_path, monkeypatch, failure, capsys
):
    import json
    import subprocess

    from apps.vaultwarden import check_restore

    calls = []
    terminated = []
    monkeypatch.setenv("BW_SESSION", "human-session-must-not-be-used")
    monkeypatch.setenv("BW_PASSWORD", "human-password-must-not-be-used")
    monkeypatch.setenv("BITWARDENCLI_APPDATA_DIR", "/human-cli-state")

    class Forward:
        def poll(self):
            return 1 if failure == "forward" else None

        def terminate(self):
            terminated.append(True)

        def wait(self, timeout):
            return 0

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def open(self, *args, **kwargs):
            return self

    def run(args, **kwargs):
        environment = kwargs["env"]
        assert environment["BITWARDENCLI_APPDATA_DIR"] == str(tmp_path / "restricted-cli")
        assert "human-session-must-not-be-used" not in environment.values()
        assert "BW_PASSWORD" not in environment
        assert "synthetic-restore-password" not in args
        assert args[-1] == "--nointeraction"
        action = args[1]
        calls.append(action)
        stdout = ""
        if action == "login":
            assert args[2] == "automation@vault.soyspray.vip"
            assert environment["BW_RESTORE_PASSWORD"] == "synthetic-restore-password"
            stdout = "isolated-session"
        if action == "get":
            assert args[2:4] == ["item", check_restore.ITEM_NAME]
            assert environment["BW_SESSION"] == "isolated-session"
            assert "BW_RESTORE_PASSWORD" not in environment
            stdout = json.dumps(
                {
                    "name": check_restore.ITEM_NAME,
                    "login": {
                        "username": "test",
                        "password": "" if failure == "record" else "test",
                    },
                }
            )
        return subprocess.CompletedProcess(
            args, 1 if failure == action else 0, stdout=stdout, stderr="synthetic-restore-password"
        )

    monkeypatch.setattr(check_restore.subprocess, "Popen", lambda *a, **k: Forward())
    monkeypatch.setattr(check_restore.subprocess, "run", run)
    monkeypatch.setattr(check_restore.ssl, "create_default_context", lambda **k: None)
    monkeypatch.setattr(check_restore.urllib.request, "build_opener", lambda *a: Response())
    if failure:
        with pytest.raises(ValueError) as error:
            check_restore.check_login(
                "restore-test",
                tmp_path,
                {},
                {
                    "email": "automation@vault.soyspray.vip",
                    "password": "synthetic-restore-password",
                },
            )
        assert "synthetic-restore-password" not in str(error.value)
    else:
        result = check_restore.check_login(
            "restore-test",
            tmp_path,
            {},
            {
                "email": "automation@vault.soyspray.vip",
                "password": "synthetic-restore-password",
            },
        )
        assert result == {"restricted_agent_login": True, "restricted_record_decryption": True}
    assert terminated == [True]
    assert calls == (
        []
        if failure == "forward"
        else ["config", "login"]
        if failure == "login"
        else ["config", "login", "sync", "get", "lock"]
    )
    assert "synthetic-restore-password" not in capsys.readouterr().out
