from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_approval_decision_matches_evidence_state():
    content = (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8")
    summary = (ROOT / "reports/gate-002-cluster-apply-and-smoke-summary.md").read_text(encoding="utf-8")
    if "Status: approved" in content:
        assert "Status: pass; runtime-verified" in summary
        assert "Runtime approval: approved" in summary
    else:
        assert "Status: pending" in content
        assert "Status: pending explicit cluster mutation permission" in summary


def test_goal_002_evidence_matches_runtime_state():
    content = (ROOT / "reports/goal-002-summary.md").read_text(encoding="utf-8").lower()
    decision = (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8")
    if "Status: approved" in decision:
        assert "runtime-verified" in content
    else:
        assert "status: pass; local-only" in content
        assert "runtime-verified" not in content


def test_goal_003_requires_runtime_approval():
    goal003 = ROOT / "soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md"
    decision = (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8")
    if goal003.exists():
        assert "Status: approved" in decision
