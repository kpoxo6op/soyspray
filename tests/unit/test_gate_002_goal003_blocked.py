from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_goal_003_body_not_created_yet():
    assert not (ROOT / "soydocs/kong-bank-lab/goals/goal-003-synthetic-bank-apis.md").exists()


def test_goal_003_block_decision_is_explicit():
    content = (ROOT / "docs/decisions/goal-003-blocked-until-kong-runtime-validation.md").read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", content)
    assert "goal-003-synthetic-bank-apis" in content
    assert "blocked until goal-002 runtime validation passes" in normalized


def test_goal_002_evidence_remains_local_only():
    content = (ROOT / "reports/goal-002-summary.md").read_text(encoding="utf-8").lower()
    assert "status: pass; local-only" in content
    assert "cluster verification\n\nnot run" in content
    assert "no; run cluster apply and smoke tests before goal-003" in content
