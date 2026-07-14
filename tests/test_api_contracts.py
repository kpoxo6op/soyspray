from __future__ import annotations

import pytest
from conftest import ROOT, load_yaml

API_KEYS = ("accounts", "payments", "cards", "customer-profile", "fraud-decisions", "open-banking")


@pytest.mark.parametrize("api", API_KEYS)
def test_api_package_is_complete(api: str) -> None:
    api_dir = ROOT / "apis/synthetic-bank" / api
    required = {
        "default.conf",
        "deployment.yaml",
        "kustomization.yaml",
        "networkpolicy-allow-kong.yaml",
        "openapi.yaml",
        "service.yaml",
    }
    assert required <= {path.name for path in api_dir.iterdir()}
    assert any(path.name.startswith("httproute-") for path in api_dir.iterdir())


@pytest.mark.parametrize("api", API_KEYS)
def test_mock_api_exposes_a_common_probe_endpoint(api: str) -> None:
    config = (ROOT / "apis/synthetic-bank" / api / "default.conf").read_text()
    assert "location = /healthz" in config
    assert "banklab-probe-ok" in config


@pytest.mark.parametrize("api", API_KEYS)
def test_api_contract_uses_current_security_profile(api: str) -> None:
    contract = load_yaml(f"apis/synthetic-bank/{api}/openapi.yaml")
    assert contract["x-banklab-api-domain"] == api
    assert contract["x-banklab-auth-profile"] == "kong-oss-auth"
    assert contract["x-banklab-data-classification"] == "synthetic"


@pytest.mark.parametrize("api", API_KEYS)
def test_routes_attach_security_plugins(api: str) -> None:
    route_file = next((ROOT / "apis/synthetic-bank" / api).glob("httproute-*.yaml"))
    route = load_yaml(str(route_file.relative_to(ROOT)))
    plugins = route["metadata"]["annotations"]["konghq.com/plugins"].split(",")
    assert plugins == [
        "banklab-jwt" if api == "open-banking" else "banklab-key-auth",
        "banklab-acl",
        "banklab-rate-limit",
        "banklab-correlation-id",
    ]


def test_catalog_matches_api_directories() -> None:
    catalog = load_yaml("apis/synthetic-bank/api-catalog.yaml")
    entries = catalog["apis"]
    assert {item["key"] for item in entries} == set(API_KEYS)
    for item in entries:
        assert item["team"]
        assert item["ns"].startswith("tenant-")
        assert item["auth_profile"] == "kong-oss-auth"
        assert item["authorization_profile"] == "acl-api-groups"
