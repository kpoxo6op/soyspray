import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("enabled", [True, False])
def test_standard_deployment_uses_native_bootstrap_and_rejects_retirement(tmp_path, enabled):
    calls = tmp_path / "calls.jsonl"
    runner = tmp_path / "ansible"
    runner.write_text(
        f"#!{sys.executable}\nimport json,sys\n"
        f"with open({str(calls)!r}, 'a') as output: output.write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    runner.chmod(0o700)
    result = subprocess.run(
        [
            "make",
            "-o",
            "go",
            "obsidian-livesync",
            f"ANSIBLE={runner}",
            f"OBSIDIAN_ENABLED={str(enabled).lower()}",
            "OBSIDIAN_REVISION=reviewed-branch",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if not enabled:
        assert result.returncode != 0
        assert not calls.exists()
        return
    assert result.returncode == 0, result.stderr
    observed = [json.loads(line) for line in calls.read_text().splitlines()]
    assert observed == [
        ["apps/obsidian-livesync/bootstrap.yml"],
        [
            "playbooks/bootstrap-apps.yml",
            "-e",
            "argocd_revision=reviewed-branch",
            "-e",
            "argocd_preview_application=obsidian-livesync",
        ],
    ]
