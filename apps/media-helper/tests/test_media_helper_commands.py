import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


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
