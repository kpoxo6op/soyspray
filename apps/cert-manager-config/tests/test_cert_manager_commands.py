import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("revision", ["HEAD", "reviewed-branch"])
def test_cert_manager_deployment_prepares_identity_before_native_root(tmp_path, revision):
    calls = tmp_path / "calls.jsonl"
    runner = tmp_path / "ansible"
    runner.write_text(
        f"#!{sys.executable}\nimport json,sys\n"
        f"with open({str(calls)!r}, 'a') as output: output.write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    runner.chmod(0o700)
    subprocess.run(
        [
            "make",
            "-o",
            "go",
            "cert-manager-config",
            f"ANSIBLE={runner}",
            f"CERT_MANAGER_CONFIG_REVISION={revision}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert [json.loads(line) for line in calls.read_text().splitlines()] == [
        ["apps/cert-manager-config/bootstrap.yml"],
        [
            "playbooks/bootstrap-apps.yml",
            "-e",
            "argocd_revision=" + revision,
            "-e",
            "argocd_preview_application=" + ("" if revision == "HEAD" else "cert-manager-config"),
        ],
    ]


@pytest.mark.parametrize("action", ["restore-check"])
def test_unsupported_cert_manager_operations_do_not_fall_back_to_deployment(action):
    result = subprocess.run(
        ["make", "--no-print-directory", "-f", "apps/cert-manager-config/Makefile", action],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "unknown:" in result.stderr
