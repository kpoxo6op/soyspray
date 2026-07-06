from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_gate_003_runtime_gate_files_exist():
    required = [
        "soydocs/kong-bank-lab/goals/gate-003-synthetic-api-runtime-apply-and-smoke.md",
        "docs/runbooks/synthetic-api-runtime-apply-and-smoke.md",
        "docs/runbooks/synthetic-api-runtime-failure.md",
        "docs/runbooks/synthetic-api-runtime-verification-evidence.md",
        "docs/decisions/goal-003-runtime-approval.md",
        "platform/kong/synthetic-apis/RUNTIME-APPLY-EXECUTION-LOG.md",
        "platform/kong/synthetic-apis/RUNTIME-SMOKE-RESULTS.md",
        "platform/kong/synthetic-apis/RUNTIME-NEGATIVE-TEST-RESULTS.md",
        "platform/kong/synthetic-apis/RUNTIME-ADMIN-API-SAFETY-RESULTS.md",
        "platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh",
        "platform/kong/synthetic-apis/scripts/collect-synthetic-api-runtime-state.sh",
        "platform/kong/synthetic-apis/scripts/verify-goal003-runtime-ready.sh",
        "scripts/validate_synthetic_api_runtime_gate.py",
        "reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md",
    ]
    missing = [relative for relative in required if not (ROOT / relative).is_file()]
    assert missing == []


def test_gate_003_validator_passes():
    from scripts.validate_synthetic_api_runtime_gate import validate

    assert validate() == []
