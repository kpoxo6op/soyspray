from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_kic_35_uses_supported_gateway_api_minor():
    versions = yaml.safe_load((ROOT / "platform/kong/versions.yaml").read_text())
    kic_tag = versions["kong_ingress_controller"]["image_tag"]
    gateway_api = versions["gateway_api"]["version"].lstrip("v")
    major, minor, *_ = [int(part) for part in gateway_api.split(".")]

    if kic_tag.startswith("3.5."):
        assert major == 1
        assert minor <= 3


def test_static_validator_enforces_kic_gateway_api_compatibility():
    from scripts.validate_kong_baseline import validate

    assert validate() == []
