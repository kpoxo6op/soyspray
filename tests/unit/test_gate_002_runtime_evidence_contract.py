import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RESULT_FILES = [
    "platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md",
    "platform/kong/CLUSTER-SMOKE-RESULTS.md",
    "platform/kong/ROUTE-SMOKE-RESULTS.md",
    "platform/kong/ADMIN-API-EXPOSURE-RESULTS.md",
]


def test_runtime_result_files_start_not_run_and_support_states():
    for relative in RESULT_FILES:
        content = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "status: not run" in content
        for state in ("not run", "pass", "fail", "blocked"):
            assert state in content


def test_cluster_apply_evidence_starts_pending_permission():
    evidence = (ROOT / "reports/gate-002-cluster-apply-and-smoke-summary.md").read_text(encoding="utf-8")
    assert "Status: pending explicit cluster mutation permission" in evidence
    assert "Explicit mutation permission required: yes" in evidence
    assert "Mutation permission granted: no" in evidence
    assert "Cluster changes performed: none" in evidence
    assert "Kong runtime applied: no" in evidence
    assert "Ready for goal 003: no" in evidence


def test_runtime_ready_check_fails_before_runtime_evidence():
    result = subprocess.run(["make", "goal002-runtime-ready"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode != 0
    assert "runtime readiness is not approved" in result.stdout
