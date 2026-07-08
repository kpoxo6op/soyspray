from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def status_line(relative: str) -> str:
    for line in (ROOT / relative).read_text(encoding="utf-8").splitlines():
        if line.startswith("Status:"):
            return line.removeprefix("Status:").strip()
    return "missing"


def runtime_results_pass() -> bool:
    return all(
        status_line(relative) == "pass"
        for relative in (
            "platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md",
            "platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md",
            "platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md",
            "platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md",
            "reports/synthetic-api-runtime-evidence.md",
            "reports/synthetic-api-route-smoke-results.md",
            "reports/synthetic-api-negative-test-results.md",
        )
    )


def test_runtime_result_files_support_required_states():
    required_states = ["not run", "pass", "fail", "blocked", "partial"]
    files = [
        "platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md",
        "platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md",
        "platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md",
        "platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md",
        "reports/synthetic-api-runtime-evidence.md",
        "reports/synthetic-api-route-smoke-results.md",
        "reports/synthetic-api-negative-test-results.md",
    ]
    for relative in files:
        content = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "status:" in content
        for state in required_states:
            assert state in content


def test_gate_summary_starts_pending_without_permission():
    content = (ROOT / "reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md").read_text(encoding="utf-8")
    if runtime_results_pass() and "Status: fail" in content:
        assert "Runtime approval: pending" in content
        assert "Ready for goal 004: no" in content
        return
    if "Status: pass; runtime-verified" in content:
        assert "Runtime approval: approved" in content
        assert "Ready for goal 004: yes" in content
        return
    assert "Status: pending explicit cluster mutation permission" in content
    assert "Mutation permission granted: no" in content
    assert "Cluster changes performed: none" in content
    assert "Runtime approval: pending" in content
    assert "Ready for goal 004: no" in content
