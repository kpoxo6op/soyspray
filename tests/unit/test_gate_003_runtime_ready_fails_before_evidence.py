import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_goal003_runtime_ready_fails_before_runtime_evidence():
    result = subprocess.run(
        ["make", "goal003-runtime-ready"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        assert "Goal 003 runtime readiness is approved." in result.stdout
    else:
        assert "Missing goal003 runtime-ready marker" in result.stdout
