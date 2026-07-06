import yaml

from scripts.synthetic_bank_config import APIS, ROOT


def test_route_matrix_matches_required_gateways():
    matrix = yaml.safe_load((ROOT / "apis/synthetic-bank/route-matrix.yaml").read_text(encoding="utf-8"))
    routes = {route["api"]: route for route in matrix["routes"]}
    assert set(routes) == {api.key for api in APIS}
    for api in APIS:
        route = routes[api.key]
        assert route["host"] == api.host
        assert route["path_prefix"] == api.prefix
        assert route["parent"] == f"platform-kong/{api.gateway}"
        assert route["namespace"] == api.namespace
        assert route["expected_marker"] == api.marker
        assert route["auth_state"] == "temporary-no-auth"


def test_only_open_banking_is_external():
    policy = yaml.safe_load((ROOT / "apis/synthetic-bank/exposure-policy.yaml").read_text(encoding="utf-8"))
    assert policy["external_allowed"] == ["open-banking"]
    assert "accounts" in policy["external_forbidden"]
    assert policy["admin_api_route_allowed"] is False
    assert policy["wildcard_hosts_allowed"] is False
    assert policy["catch_all_routes_allowed"] is False
    assert policy["temporary_no_auth"] == "temporary-no-auth"
