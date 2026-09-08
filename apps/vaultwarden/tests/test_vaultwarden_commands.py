import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_private_input_bootstrap_does_not_submit_an_application(tmp_path):
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
            "--no-print-directory",
            "-f",
            "apps/vaultwarden/Makefile",
            "bootstrap",
            f"ANSIBLE={runner}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    observed = [json.loads(line) for line in calls.read_text().splitlines()]
    assert observed == [
        ["apps/vaultwarden/bootstrap.yml"],
    ]
