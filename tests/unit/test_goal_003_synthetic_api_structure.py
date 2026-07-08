from pathlib import Path

import yaml

from scripts.synthetic_bank_config import APIS, ROOT


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_all_six_synthetic_apis_have_required_files():
    required = {
        "README.md",
        "openapi.yaml",
        "ownership.yaml",
        "kustomization.yaml",
        "configmap-mock-responses.yaml",
        "deployment.yaml",
        "service.yaml",
        "networkpolicy-allow-kong.yaml",
        "tests/positive.yaml",
        "tests/negative.yaml",
    }
    for api in APIS:
        route_file = "httproute-external.yaml" if api.exposure == "external" else "httproute-internal.yaml"
        missing = [name for name in required | {route_file} if not (ROOT / "apis/synthetic-bank" / api.key / name).is_file()]
        assert missing == []


def test_api_manifests_use_expected_namespaces_and_labels():
    for api in APIS:
        for name in ("deployment.yaml", "service.yaml", "networkpolicy-allow-kong.yaml"):
            doc = load(ROOT / "apis/synthetic-bank" / api.key / name)
            assert doc["metadata"]["namespace"] == api.namespace
            labels = doc["metadata"]["labels"]
            assert labels["banklab.konghq.com/platform-layer"] == "synthetic-api"
            assert labels["banklab.konghq.com/auth-profile"] == "none-temporary-goal003-sandbox"
            assert labels["banklab.konghq.com/auth-state"] == "temporary-no-auth"
            assert labels["banklab.konghq.com/goal"] == "goal-003"


def test_synthetic_api_tenant_namespaces_use_prereq_layer():
    for api in APIS:
        namespace = load(ROOT / "platform/namespaces" / f"{api.namespace}.yaml")
        assert namespace["kind"] == "Namespace"
        assert namespace["metadata"]["name"] == api.namespace
        labels = namespace["metadata"]["labels"]
        assert labels["banklab.konghq.com/managed-by"] == "gitops"
        assert labels["banklab.konghq.com/platform-layer"] == "prereq"
        assert labels["banklab.konghq.com/environment"] == "lab"
        assert labels["banklab.konghq.com/data-classification"] == "synthetic"
        assert labels["banklab.konghq.com/owner"] == api.owner


def test_synthetic_api_static_validator_passes():
    from scripts.validate_synthetic_bank_apis import validate

    assert validate() == []
