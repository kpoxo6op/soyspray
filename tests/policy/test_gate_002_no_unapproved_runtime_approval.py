from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_approval_decision_is_pending():
    content = (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8")
    assert "Status: pending" in content
    assert "Status: approved" in content
    assert content.index("Status: pending") < content.index("Status: approved")


def test_goal_002_evidence_not_runtime_verified_yet():
    content = (ROOT / "reports/goal-002-summary.md").read_text(encoding="utf-8").lower()
    assert "status: pass; local-only" in content
    assert "runtime-verified" not in content


def test_goal_003_still_not_created():
    assert not (ROOT / "soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md").exists()
