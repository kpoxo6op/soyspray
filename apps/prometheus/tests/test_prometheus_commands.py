import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_diff_covers_the_stack_and_disposable_configuration():
    result = subprocess.run(
        ["make", "--no-print-directory", "-n", "-f", "apps/prometheus/Makefile", "diff"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    assert "--app kube-prometheus-stack --package apps/prometheus" in result.stdout
    assert "--app prometheus-config --package apps/prometheus/config" in result.stdout


def test_bootstrap_only_prepares_private_inputs():
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            "apps/prometheus/Makefile",
            "bootstrap",
            "ANSIBLE=echo ansible-playbook",
        ],
        cwd=ROOT,
        env=os.environ,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    assert result.stdout.splitlines()[-1] == "ansible-playbook apps/prometheus/bootstrap.yml"


@pytest.mark.parametrize("action", ["restore-check", "smoke", "deploy"])
def test_unknown_operations_do_not_run_ansible(tmp_path, action):
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
    assert "unknown:" in result.stderr
    assert not marker.exists()
