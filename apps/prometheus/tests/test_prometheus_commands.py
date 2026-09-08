import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("action", ["deploy", "restore-check", "smoke"])
def test_blocked_operations_do_not_run_ansible(tmp_path, action):
    marker = tmp_path / "ansible-ran"
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            "apps/prometheus/Makefile",
            action,
            f"ANSIBLE=touch {marker}",
        ],
        cwd=ROOT,
        env=os.environ,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert ("blocked:" if action == "deploy" else "unknown:") in result.stderr
    assert not marker.exists()
