"""Protect the command recorder used by the native node drill."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "playbooks/operations/nodes/drill-v2/record.sh"


def test_recorder_preserves_exit_status_arguments_and_log_privacy(tmp_path):
    evidence = tmp_path / "private evidence"
    command = [
        "bash",
        str(RECORDER),
        str(evidence),
        "failed",
        sys.executable,
        "-c",
        "import sys; print(sys.argv[1]); sys.exit(42)",
        "literal $(false) `false`",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 42
    log = evidence / "failed.log"
    original = log.read_text()
    assert original == "literal $(false) `false`\n"
    journal = (evidence / "journal.tsv").read_text()
    assert "\tSTART\tfailed\t" in journal and "\tEND\tfailed\trc=42" in journal
    assert evidence.stat().st_mode & 0o777 == 0o700
    assert log.stat().st_mode & 0o777 == 0o600
    repeat = subprocess.run(command, capture_output=True, text=True, check=False)
    assert repeat.returncode == 2
    assert log.read_text() == original
