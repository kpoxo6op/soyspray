"""A fault-injection pause must retain a verifiable restoration path."""

import os
import signal
import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[1] / "playbooks/operations/voice/gi-pause.sh"


@pytest.fixture
def child():
    process = subprocess.Popen(["sleep", "60"])
    yield process
    os.kill(process.pid, signal.SIGCONT)
    process.terminate()
    process.wait(timeout=5)


def identity(process):
    return Path(f"/proc/{process.pid}/stat").read_text().split()[21]


def state(process):
    return Path(f"/proc/{process.pid}/stat").read_text().split()[2]


def test_changed_process_is_refused_before_any_pause(child):
    result = subprocess.run(
        [str(HELPER), "freeze", str(child.pid), "1", "360", "test"], capture_output=True
    )
    assert result.returncode == 3
    assert state(child) != "T"


def test_matching_process_is_resumed(child):
    os.kill(child.pid, signal.SIGSTOP)
    result = subprocess.run(
        [str(HELPER), "restore", str(child.pid), identity(child)], capture_output=True
    )
    assert result.returncode == 0
    assert b"VOICE_CONT" in result.stdout
    assert state(child) != "T"


def test_restore_arm_failure_never_pauses_process(child, tmp_path):
    stub = tmp_path / "systemd-run"
    stub.write_text("#!/bin/sh\nexit 1\n")
    stub.chmod(0o755)
    result = subprocess.run(
        [str(HELPER), "freeze", str(child.pid), identity(child), "360", "test"],
        env={**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin"},
        capture_output=True,
    )
    assert result.returncode != 0
    assert state(child) != "T"
