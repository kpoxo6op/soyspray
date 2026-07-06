from pathlib import Path

from scripts.validate_cluster_apply_gate import validate


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/gate-002-cluster-apply-and-smoke.md",
    "docs/runbooks/kong-cluster-apply-and-smoke.md",
    "docs/runbooks/kong-cluster-apply-failure.md",
    "docs/runbooks/kong-runtime-verification-evidence.md",
    "docs/decisions/goal-002-runtime-approval.md",
    "platform/kong/CLUSTER-APPLY-EXECUTION-LOG.md",
    "platform/kong/CLUSTER-SMOKE-RESULTS.md",
    "platform/kong/ROUTE-SMOKE-RESULTS.md",
    "platform/kong/ADMIN-API-EXPOSURE-RESULTS.md",
    "platform/kong/scripts/kong-cluster-apply-and-smoke.sh",
    "platform/kong/scripts/collect-kong-runtime-evidence.sh",
    "platform/kong/scripts/verify-goal002-runtime-ready.sh",
    "scripts/validate_cluster_apply_gate.py",
    "reports/gate-002-cluster-apply-and-smoke-summary.md",
]


def test_cluster_apply_gate_required_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_cluster_apply_gate_validator_passes_locally():
    assert validate() == []
