import yaml

from scripts.synthetic_bank_config import APIS, ROOT


def test_ownership_metadata_matches_api_matrix():
    for api in APIS:
        ownership = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / "ownership.yaml").read_text(encoding="utf-8"))
        assert ownership["api_name"] == f"synthetic-{api.key}-api"
        assert ownership["tenant_namespace"] == api.namespace
        assert ownership["owning_team"] == api.owner
        assert ownership["route_host"] == api.host
        assert ownership["route_paths"] == [api.prefix]
        assert ownership["auth_profile"] == "none-temporary-goal003-sandbox"
        assert ownership["auth_state"] == "temporary-no-auth"
        assert ownership["authorization_profile"] == "none-temporary-goal003-sandbox"
        assert ownership["rate_limit_profile"] == "deferred-goal004"
        assert ownership["future_auth_goal"] == "goal-004-auth-rate-limit-security"
