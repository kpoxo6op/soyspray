from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_goal_003_body_requires_runtime_approval():
    goal003 = ROOT / "soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md"
    decision = (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8")
    if goal003.exists():
        assert "Status: approved" in decision


def test_goal_003_block_decision_is_explicit():
    content = (ROOT / "docs/decisions/goal-003-blocked-until-kong-runtime-validation.md").read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", content)
    assert "goal-003-synthetic-bank-apis" in content
    assert "blocked until goal-002 runtime validation passes" in normalized
    if "Status: approved" in (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8"):
        assert "Runtime condition is now satisfied" in content


def test_goal_002_evidence_matches_runtime_state():
    content = (ROOT / "reports/goal-002-summary.md").read_text(encoding="utf-8").lower()
    decision = (ROOT / "docs/decisions/goal-002-runtime-approval.md").read_text(encoding="utf-8")
    if "Status: approved" in decision:
        assert "status: pass; runtime-verified" in content
        assert "runtime-verified on kubernetes context" in content
        assert "yes; ask chatgpt pro for `goal-003-synthetic-bank-apis`" in content
    else:
        assert "status: pass; local-only" in content
        assert "cluster verification\n\nnot run" in content
        assert "no; run cluster apply and smoke tests before goal-003" in content
