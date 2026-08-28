from __future__ import annotations

import json
import os
import stat
import subprocess
import sys

from conftest import ROOT

AGENT_SECRET = ROOT / "scripts/agent-secret"


def write_executable(path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_agent_secret_reads_only_the_hays_item_without_password_arguments(tmp_path) -> None:
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
elif command == "get":
    print(json.dumps({"login": {"username": "hays-user", "password": "hays-pass"}}))
""",
    )
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}:{environment['PATH']}"
    environment["AGENT_SECRET_CALL_LOG"] = str(call_log)
    environment["XDG_STATE_HOME"] = str(tmp_path / "state")

    results = [
        subprocess.run(
            [sys.executable, AGENT_SECRET, "read", "hays-online-timesheets"],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        for _ in range(2)
    ]

    for result in results:
        assert json.loads(result.stdout) == {
            "username": "hays-user",
            "password": "hays-pass",
        }
    calls = call_log.read_text()
    assert calls.count("config server https://vault.soyspray.vip") == 1
    assert calls.count("login agent@example.test --passwordenv BW_PASSWORD --raw") == 1
    assert calls.count("unlock --passwordenv BW_PASSWORD --raw") == 1
    assert "sync" in calls
    assert "get item hays-online-timesheets" in calls
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
    print(json.dumps({"login": {"username": "hays-user", "password": "hays-pass"}}))
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
