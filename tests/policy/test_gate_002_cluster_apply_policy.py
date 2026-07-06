import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_validates_gate_but_does_not_run_cluster_apply_paths():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "make validate-cluster-apply-gate" in ci
    forbidden = [
        "cluster-readonly-preflight",
        "kong-readonly-preflight",
        "cluster-smoke",
        "cluster-prereq-smoke",
        "kong-install-dry-run",
        "kong-apply",
        "kong-cluster-smoke",
        "kong-route-smoke",
        "kong-rollback",
    ]
    for target in forbidden:
        assert not re.search(rf"run:\s+make\s+{re.escape(target)}(?:\s|$)", ci)
    assert "kong-cluster-apply-and-smoke.sh" not in ci


def test_cluster_apply_script_uses_make_guardrails():
    content = (ROOT / "platform/kong/scripts/kong-cluster-apply-and-smoke.sh").read_text(encoding="utf-8")
    assert "make kong-apply" in content
    assert "kubectl apply" not in content
    assert "helm upgrade" not in content
    assert "argocd app sync" not in content
