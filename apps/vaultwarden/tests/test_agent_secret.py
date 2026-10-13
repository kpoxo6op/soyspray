from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from apps.vaultwarden import agent_secret

ROOT = Path(__file__).resolve().parents[3]

AGENT_SECRET = ROOT / "scripts/agent-secret"


def write_executable(path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.mark.parametrize(
    "name",
    ["hays-online-timesheets", "Phone unlock PIN", "ASB app login", "BNZ app login"],
)
def test_agent_secret_reads_allowlisted_items_without_password_arguments(tmp_path, name) -> None:
    """CLI returns approved credentials after fresh login and cached unlock, never on argv."""
    call_log = tmp_path / "calls.log"
    write_executable(
        tmp_path / "kubectl",
        """#!/usr/bin/env python3
import base64
import json
import os
import sys

with open(os.environ["AGENT_SECRET_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write("kubectl " + " ".join(sys.argv[1:]) + "\\n")

print(json.dumps({"data": {
    "email": base64.b64encode(b"agent@example.test").decode(),
    "master-password": base64.b64encode(b"bootstrap-password").decode(),
}}))
""",
    )
    write_executable(
        tmp_path / "bw",
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

with open(os.environ["AGENT_SECRET_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(sys.argv[1:]) + "\\n")

command = sys.argv[1]
appdata = Path(os.environ["BITWARDENCLI_APPDATA_DIR"])
appdata.mkdir(parents=True, exist_ok=True)
login_marker = appdata / "logged-in"
if command == "config" and login_marker.exists():
    raise SystemExit(1)
elif command == "status":
    print(json.dumps({
        "status": "locked" if login_marker.exists() else "unauthenticated",
        "userEmail": "agent@example.test" if login_marker.exists() else None,
    }))
elif command == "login":
    assert "--passwordenv" in sys.argv
    assert os.environ["BW_PASSWORD"] == "bootstrap-password"
    login_marker.touch()
    print("test-session")
elif command == "unlock":
    assert "--passwordenv" in sys.argv
    assert os.environ["BW_PASSWORD"] == "bootstrap-password"
    print("test-session")
elif command in ("get", "list"):
    name = sys.argv[3] if command == "get" else sys.argv[4]
    item = {"name": name, "login": {
        "username": "hays-user" if name == "hays-online-timesheets" else None,
        "password": "hays-pass",
    }}
    print(json.dumps(item if command == "get" else [item]))
""",
    )
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}:{environment['PATH']}"
    environment["AGENT_SECRET_CALL_LOG"] = str(call_log)
    environment["XDG_STATE_HOME"] = str(tmp_path / "state")

    results = [
        subprocess.run(
            [sys.executable, AGENT_SECRET, "read", name],
            cwd=tmp_path,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        for _ in range(2)
    ]

    for result in results:
        expected = {"username": "hays-user", "password": "hays-pass"}
        if name != "hays-online-timesheets":
            expected.update(username="", pin="hays-pass")
        assert json.loads(result.stdout) == expected
    calls = call_log.read_text()
    assert calls.count("config server https://vault.soyspray.vip") == 1
    assert calls.count("login agent@example.test --passwordenv BW_PASSWORD --raw") == 1
    assert calls.count("unlock --passwordenv BW_PASSWORD --raw") == 1
    assert "sync" in calls
    if name == "hays-online-timesheets":
        assert f"get item {name}" in calls
    else:
        assert f"list items --search {name}" in calls
    assert "kubectl -n vaultwarden get secret vaultwarden-agent-login -o json" in calls
    assert "vaultwarden-agent-bootstrap" not in calls
    assert "bootstrap-password" not in calls
    assert "hays-pass" not in calls


def test_agent_secret_rejects_other_item_names() -> None:
    result = subprocess.run(
        [sys.executable, AGENT_SECRET, "read", "another-item"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "hays-online-timesheets" in result.stderr


def test_agent_secret_replaces_a_cached_human_login(tmp_path) -> None:
    call_log = tmp_path / "calls.log"
    write_executable(
        tmp_path / "kubectl",
        """#!/usr/bin/env python3
import base64
import json

print(json.dumps({"data": {
    "email": base64.b64encode(b"agent@example.test").decode(),
    "master-password": base64.b64encode(b"agent-password").decode(),
}}))
""",
    )
    write_executable(
        tmp_path / "bw",
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

with open(os.environ["AGENT_SECRET_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(sys.argv[1:]) + "\\n")

command = sys.argv[1]
logout_marker = Path(os.environ["AGENT_SECRET_CALL_LOG"]).with_suffix(".logout")
if command == "status":
    print(json.dumps({"status": "locked", "userEmail": "human@example.test"}))
elif command == "logout":
    logout_marker.touch()
elif command == "config":
    assert logout_marker.exists()
elif command == "login":
    assert logout_marker.exists()
    assert sys.argv[2] == "agent@example.test"
    assert os.environ["BW_PASSWORD"] == "agent-password"
    print("agent-session")
elif command == "unlock":
    raise SystemExit(9)
elif command == "get":
    print(json.dumps({"name": "hays-online-timesheets", "login": {"username": "hays-user", "password": "hays-pass"}}))
""",
    )
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}:{environment['PATH']}"
    environment["AGENT_SECRET_CALL_LOG"] = str(call_log)
    environment["XDG_STATE_HOME"] = str(tmp_path / "state")

    result = subprocess.run(
        [sys.executable, AGENT_SECRET, "read", "hays-online-timesheets"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "username": "hays-user",
        "password": "hays-pass",
    }
    calls = call_log.read_text()
    assert calls.index("logout") < calls.index("login agent@example.test")
    assert "unlock" not in calls


@pytest.mark.parametrize(
    "fault", ["different-name", "duplicate-name", "deleted", "duplicate-pin", "invalid-pin"]
)
def test_reader_rejects_unsafe_phone_response_and_locks(tmp_path, monkeypatch, fault):
    """A wrong/deleted item or ambiguous field must never leave credentials usable."""
    item = {"name": "Phone unlock PIN", "login": {"password": "test-only", "username": None}}
    if fault == "different-name":
        item["name"] = "unapproved record"
    elif fault == "deleted":
        item["deletedDate"] = "2026-01-01"
    elif fault == "duplicate-pin":
        item["fields"] = [{"name": "pin", "value": "test-only"}, {"name": "PIN", "value": "other"}]
    elif fault == "invalid-pin":
        item["fields"] = [{"name": "pin", "value": None}]
    calls = []

    def fake_run(command, environment=None):
        calls.append(command[:2])
        if command[1] == "status":
            return json.dumps({"status": "locked", "userEmail": "agent@example.test"})
        if command[1] == "unlock":
            assert "BW_SESSION" not in environment
            return "test-session"
        if command[1] == "list":
            return json.dumps([item, item] if fault == "duplicate-name" else [item])
        return ""

    monkeypatch.setenv("BW_SESSION", "inherited-human-session")
    monkeypatch.setattr(agent_secret.shutil, "which", lambda name: name)
    monkeypatch.setattr(agent_secret, "appdata_directory", lambda: tmp_path)
    monkeypatch.setattr(agent_secret, "read_bootstrap", lambda: ("agent@example.test", "test-only"))
    monkeypatch.setattr(agent_secret, "run", fake_run)
    with pytest.raises(agent_secret.AgentSecretError):
        agent_secret.read_item("Phone unlock PIN")
    assert calls[-1] == ["bw", "lock"]


def test_import_rejects_unapproved_name_before_bootstrap(monkeypatch):
    """Import callers cannot bypass the CLI allowlist to read another record."""

    def forbidden():
        pytest.fail("unapproved name reached bootstrap")

    monkeypatch.setattr(agent_secret, "read_bootstrap", forbidden)
    with pytest.raises(agent_secret.AgentSecretError, match="not allowed"):
        agent_secret.read_item("another-item")
