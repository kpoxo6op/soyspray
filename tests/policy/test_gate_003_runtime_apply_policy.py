import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def target_block(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
    return match.group("body") if match else ""


def test_gate_003_mutating_paths_are_guarded_and_not_in_ci():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    runtime_script = (ROOT / "platform/kong/synthetic-apis/scripts/synthetic-api-runtime-apply-and-smoke.sh").read_text(encoding="utf-8")
    apply_script = (ROOT / "platform/kong/synthetic-apis/scripts/synthetic-api-apply.sh").read_text(encoding="utf-8")
    dry_run_script = (ROOT / "platform/kong/synthetic-apis/scripts/synthetic-api-install-dry-run.sh").read_text(encoding="utf-8")

    assert "require-cluster-mutation-permission.sh" in target_block(makefile, "synthetic-api-apply")
    assert "require-cluster-mutation-permission.sh" in target_block(makefile, "synthetic-api-rollback")
    assert "require-cluster-mutation-permission.sh" in runtime_script
    assert "--include-kind Namespace" in apply_script
    assert "--exclude-kind Namespace" in apply_script
    assert "--include-kind Namespace" in dry_run_script
    assert "--dry-run=client" in dry_run_script
    assert "make validate-synthetic-api-runtime-gate" in ci

    forbidden_targets = [
        "synthetic-api-install-dry-run",
        "synthetic-api-apply",
        "synthetic-api-smoke",
        "synthetic-api-negative-test",
        "synthetic-api-rollback",
        "synthetic-api-runtime-ready",
        "goal003-runtime-ready",
    ]
    for target in forbidden_targets:
        assert not re.search(rf"run:\s+make\s+{re.escape(target)}(?:\s|$)", ci)
    assert "synthetic-api-runtime-apply-and-smoke.sh" not in ci
