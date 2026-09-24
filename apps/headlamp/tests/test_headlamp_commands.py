import copy
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.app_diff_sources import revision_arguments

ROOT = Path(__file__).resolve().parents[3]


def test_chart_version_change_supports_native_revision_comparison():
    desired = yaml.safe_load((ROOT / "apps/headlamp/argocd/application.yaml").read_text())
    desired["spec"]["sources"][0]["targetRevision"] = "9.8.7"
    live = copy.deepcopy(desired)
    live["spec"]["sources"][0]["targetRevision"] = "9.8.6"
    assert revision_arguments(
        live, desired, "https://github.com/kpoxo6op/soyspray.git", "reviewed-commit"
    ) == [
        "--source-positions",
        "1",
        "--revisions",
        "9.8.7",
        "--source-positions",
        "2",
        "--revisions",
        "reviewed-commit",
    ]


@pytest.mark.parametrize("action", ["smoke", "restore-check"])
def test_unsupported_headlamp_operations_do_not_fall_back_to_deployment(action):
    result = subprocess.run(
        ["make", "--no-print-directory", "-f", "apps/headlamp/Makefile", action],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "unknown:" in result.stderr
