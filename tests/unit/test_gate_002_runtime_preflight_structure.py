from pathlib import Path
import re

from scripts.validate_runtime_preflight import validate


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/gate-002-runtime-preflight.md",
    "docs/architecture/kong-runtime-validation-gate.md",
    "docs/architecture/cluster-mutation-guardrails.md",
    "docs/runbooks/kong-runtime-preflight.md",
    "docs/runbooks/kong-runtime-apply-checklist.md",
    "docs/runbooks/kong-runtime-smoke-checklist.md",
    "docs/runbooks/kong-runtime-rollback-checklist.md",
    "platform/kong/PRE-CLUSTER-APPLY-CHECKLIST.md",
    "platform/kong/CLUSTER-APPLY-REQUEST.md",
    "platform/kong/RUNTIME-VALIDATION-CHECKLIST.md",
    "platform/kong/ROLLBACK-CHECKLIST.md",
    "reports/gate-002-runtime-preflight-summary.md",
]


def test_gate_002_runtime_preflight_required_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_runtime_preflight_validator_passes():
    assert validate() == []


def test_apply_plan_declares_runtime_boundary():
    content = (ROOT / "reports/kong-runtime-apply-plan.md").read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", content.lower())
    assert "does not prove runtime success" in content.lower()
    assert "explicit cluster apply and smoke validation" in normalized
