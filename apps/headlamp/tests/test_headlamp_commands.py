import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.app_diff_sources import revision_arguments

ROOT = Path(__file__).resolve().parents[3]


def test_exact_existing_chart_version_supports_native_revision_comparison():
    desired = yaml.safe_load((ROOT / "apps/headlamp/argocd/application.yaml").read_text())
    live = copy.deepcopy(desired)
    live["spec"]["sources"][0]["targetRevision"] = "0.35"
    assert desired["spec"]["sources"][0]["targetRevision"] == "0.35.0"
    assert revision_arguments(
        live, desired, "https://github.com/kpoxo6op/soyspray.git", "reviewed-commit"
    ) == [
        "--source-positions",
        "1",
        "--revisions",
        "0.35.0",
        "--source-positions",
        "2",
        "--revisions",
        "reviewed-commit",
    ]


@pytest.mark.parametrize("revision", ["HEAD", "reviewed-branch"])
def test_headlamp_deployment_uses_only_native_root_and_keeps_identity_ownership(tmp_path, revision):
    calls = tmp_path / "calls.jsonl"
    runner = tmp_path / "ansible"
    runner.write_text(
        f"#!{sys.executable}\nimport json,sys\n"
        f"with open({str(calls)!r}, 'a') as output: output.write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    runner.chmod(0o700)
    subprocess.run(
        ["make", "-o", "go", "headlamp", f"ANSIBLE={runner}", f"HEADLAMP_REVISION={revision}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert [json.loads(line) for line in calls.read_text().splitlines()] == [
        [
            "playbooks/bootstrap-apps.yml",
            "-e",
            "argocd_revision=" + revision,
            "-e",
            "argocd_preview_application=" + ("" if revision == "HEAD" else "headlamp"),
        ]
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
