import yaml

from scripts.synthetic_bank_config import APIS, AUTH_PROFILE, AUTH_STATE, AUTHORIZATION_PROFILE, ROOT, RUNTIME_CREDENTIAL_SOURCE, api_access_group, api_rate_limit_profile


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
        assert route["auth_profile"] == AUTH_PROFILE
        assert route["auth_state"] == AUTH_STATE
        assert route["authorization_profile"] == AUTHORIZATION_PROFILE
        assert route["access_group"] == api_access_group(api.key)
        assert route["rate_limit_profile"] == api_rate_limit_profile(api.exposure)


def test_only_open_banking_is_external():
    policy = yaml.safe_load((ROOT / "apis/synthetic-bank/exposure-policy.yaml").read_text(encoding="utf-8"))
    assert policy["external_allowed"] == ["open-banking"]
    assert "accounts" in policy["external_forbidden"]
    assert policy["admin_api_route_allowed"] is False
    assert policy["wildcard_hosts_allowed"] is False
    assert policy["catch_all_routes_allowed"] is False
    assert policy["authentication_required"] == AUTH_STATE
    assert policy["authorization_required"] == AUTHORIZATION_PROFILE
    assert policy["rate_limiting_required"] == "goal004-redis-rate-limits"
    assert policy["credential_source"] == RUNTIME_CREDENTIAL_SOURCE
