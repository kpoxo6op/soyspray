from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_goal004_is_blocked_before_goal003_runtime_approval():
    decision = (ROOT / "docs/decisions/goal-003-runtime-approval.md").read_text(encoding="utf-8")
    summary = (ROOT / "reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md").read_text(encoding="utf-8")
    goal003 = (ROOT / "reports/goal-003-summary.md").read_text(encoding="utf-8")

    if "Status: approved" not in decision:
        assert not (ROOT / "soydocs/kong-bank-lab/goals/goal-004-auth-rate-limit-security.md").exists()
        assert "Ready for goal 004: no" in summary
        assert "Runtime approval: pending" in summary
        assert "Ready for next goal: no" in goal003
