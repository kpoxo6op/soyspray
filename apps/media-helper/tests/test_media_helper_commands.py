import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("revision", ["HEAD", "reviewed-branch"])
def test_media_helper_deployment_uses_only_native_root_and_keeps_identity_ownership(
    tmp_path, revision
):
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
            "media-helper",
            f"ANSIBLE={runner}",
            f"MEDIA_HELPER_REVISION={revision}",
        ],
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
            "argocd_preview_application=" + ("" if revision == "HEAD" else "media-helper"),
        ]
    ]


@pytest.mark.parametrize("action", ["smoke", "restore-check"])
def test_unsupported_media_helper_operations_do_not_fall_back_to_deployment(action):
    result = subprocess.run(
        ["make", "--no-print-directory", "-f", "apps/media-helper/Makefile", action],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "unknown:" in result.stderr
