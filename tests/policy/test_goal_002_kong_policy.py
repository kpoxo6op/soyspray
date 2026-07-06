from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_kong_static_validator_passes():
    from scripts.validate_kong_baseline import validate

    assert validate() == []


def test_smoke_backend_is_not_business_api():
    deployment = load("platform/kong/smoke/deployment.yaml")
    labels = deployment["spec"]["template"]["metadata"]["labels"]
    assert labels["banklab.konghq.com/not-business-api"] == "true"


def test_argocd_templates_are_not_deployable_until_repo_url_replaced():
    for path in list((ROOT / "platform/kong/argocd").glob("*.yaml")) + [
        ROOT / "platform/gitops/app-of-apps/kong-baseline-app.yaml"
    ]:
        assert "REPLACE_WITH_REPO_URL" in path.read_text()


def test_kic_gateway_api_pair_is_supported_by_kong_matrix():
    versions = load("platform/kong/versions.yaml")
    kic_tag = versions["kong_ingress_controller"]["image_tag"]
    gateway_api = versions["gateway_api"]["version"].lstrip("v")
    major, minor, *_ = [int(part) for part in gateway_api.split(".")]
    assert kic_tag.startswith("3.5.")
    assert (major, minor) <= (1, 3)
