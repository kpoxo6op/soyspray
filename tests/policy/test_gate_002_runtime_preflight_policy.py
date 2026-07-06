from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_preflight_keeps_goal_002_version_pins():
    versions = yaml.safe_load((ROOT / "platform/kong/versions.yaml").read_text(encoding="utf-8"))
    assert versions["kong_gateway"]["image_repository"] == "kong"
    assert versions["kong_gateway"]["image_tag"] == "3.9.3"
    assert versions["kong_ingress_controller"]["image_tag"] == "3.5.10"
    assert versions["gateway_api"]["version"] == "v1.3.0"


def test_runtime_preflight_evidence_declares_no_runtime_claims():
    evidence = (ROOT / "reports/gate-002-runtime-preflight-summary.md").read_text(encoding="utf-8").lower()
    assert "cluster changes performed: none" in evidence
    assert "secrets created: none" in evidence
    assert "kong runtime applied: no" in evidence
    assert "kong route smoke passed: no" in evidence
    assert "admin api externally exposed: no, based on static validation only" in evidence


def test_cluster_apply_request_requires_explicit_approval():
    request = (ROOT / "platform/kong/CLUSTER-APPLY-REQUEST.md").read_text(encoding="utf-8")
    assert "Do not run cluster-mutating commands until approval is explicitly granted." in request
    assert "BANKLAB_ALLOW_CLUSTER_MUTATION=true" in request
    assert "BANKLAB_TARGET_CONTEXT=<expected-context>" in request
