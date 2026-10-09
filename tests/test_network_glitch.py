"""Independent recovery must be armed before the disruptive command.

The shell boundary can fail even when Ansible syntax passes. These tests run
the real operation with fake host utilities; they never touch a network.
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "playbooks/operations/networking/network-glitch.sh"


@pytest.mark.parametrize("arm_fails", [False, True])
def test_recovery_is_armed_before_down_and_up_runs_after_sleep_failure(tmp_path, arm_fails):
    log = tmp_path / "calls"
    for name, body in {
        "systemd-run": 'echo "arm $*" >> "$CALLS"; exit "$ARM_FAILS"',
        "systemctl": 'echo "verify $*" >> "$CALLS"',
        "ip": 'echo "ip $*" >> "$CALLS"',
        "sleep": 'echo "sleep $*" >> "$CALLS"; exit 42',
    }.items():
        executable = tmp_path / name
        executable.write_text(f"#!/bin/sh\n{body}\n")
        executable.chmod(0o700)
    result = subprocess.run(
        ["bash", str(SCRIPT), "eno1", "30", "soyspray-network-test"],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "CALLS": str(log),
            "ARM_FAILS": str(int(arm_fails)),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    calls = log.read_text().splitlines()
    if arm_fails:
        assert result.returncode == 1
        assert len(calls) == 1
        assert not any(call.startswith("ip ") for call in calls)
    else:
        assert result.returncode == 42
        assert calls[0].startswith("arm ") and "--on-active=30s" in calls[0]
        assert calls[1].startswith("verify ")
        assert calls[2:] == ["ip link set dev eno1 down", "sleep 30", "ip link set dev eno1 up"]


@pytest.mark.parametrize("duration", ["0", "9", "121", "30;false"])
def test_invalid_duration_is_rejected_before_host_commands(duration):
    result = subprocess.run(
        ["bash", str(SCRIPT), "eno1", duration, "soyspray-network-test"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "NETWORK_DOWN" not in result.stdout
