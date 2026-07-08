import yaml

from scripts.synthetic_bank_config import APIS, AUTH_PROFILE, AUTH_STATE, AUTHORIZATION_PROFILE, ROOT, RUNTIME_CREDENTIAL_SOURCE, api_access_group, api_rate_limit_profile


def test_ownership_metadata_matches_api_matrix():
    for api in APIS:
        ownership = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / "ownership.yaml").read_text(encoding="utf-8"))
        assert ownership["api_name"] == f"synthetic-{api.key}-api"
        assert ownership["tenant_namespace"] == api.namespace
        assert ownership["owning_team"] == api.owner
        assert ownership["route_host"] == api.host
        assert ownership["route_paths"] == [api.prefix]
        assert ownership["auth_profile"] == AUTH_PROFILE
        assert ownership["auth_state"] == AUTH_STATE
        assert ownership["authorization_profile"] == AUTHORIZATION_PROFILE
        assert ownership["access_group"] == api_access_group(api.key)
        assert ownership["rate_limit_profile"] == api_rate_limit_profile(api.exposure)
        assert ownership["credential_source"] == RUNTIME_CREDENTIAL_SOURCE
        assert ownership["implemented_auth_goal"] == "goal-004-auth-rate-limit-security"
