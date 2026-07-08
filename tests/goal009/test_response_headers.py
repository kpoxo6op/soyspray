from scripts.goal008_governance_policy_config import load_policy as load_goal008_policy
from scripts.goal009_response_headers_config import (
    API_ID,
    NAMESPACE,
    PLUGIN_NAME,
    PLUGIN_TYPE,
    REQUIRED_BASE_PLUGINS,
    REQUIRED_HEADER_LINES,
    ROUTE_NAME,
)
from scripts.render_goal009_response_headers import render, rollback_resources, stable_accounts_route, unsafe_request_transformer_fixture
from scripts.validate_goal009_response_headers import plugin_annotation_list, validate, validate_docs


def docs(kind, rendered=None):
    rendered = render() if rendered is None else rendered
    return [doc for doc in rendered if doc.get("kind") == kind]


def test_rendered_response_headers_are_namespaced_and_oss_only():
    rendered = render()
    assert [doc for doc in rendered if doc.get("kind") == "KongPlugin"]
    assert [doc for doc in rendered if doc.get("kind") == "HTTPRoute"]
    assert not [doc for doc in rendered if doc.get("kind") == "Secret"]
    assert not [doc for doc in rendered if doc.get("kind") == "KongClusterPlugin"]
    plugin = docs("KongPlugin")[0]
    assert plugin["metadata"]["namespace"] == NAMESPACE
    assert plugin["plugin"] == PLUGIN_TYPE


def test_plugin_adds_only_required_governed_headers():
    plugin = docs("KongPlugin")[0]
    assert plugin["metadata"]["name"] == PLUGIN_NAME
    assert plugin["config"]["add"]["headers"] == list(REQUIRED_HEADER_LINES)


def test_route_preserves_existing_plugins_and_appends_goal009_plugin():
    base_plugins = plugin_annotation_list(stable_accounts_route())
    route = docs("HTTPRoute")[0]
    assert route["metadata"]["name"] == ROUTE_NAME
    assert route["metadata"]["namespace"] == NAMESPACE
    plugins = plugin_annotation_list(route)
    assert plugins[: len(base_plugins)] == base_plugins
    for base_plugin in REQUIRED_BASE_PLUGINS:
        assert base_plugin in plugins
    assert plugins[-1] == PLUGIN_NAME
    assert plugins.count(PLUGIN_NAME) == 1
    assert route["metadata"]["labels"]["platform.soyspray.io/api-id"] == API_ID


def test_rollback_route_omits_goal009_plugin():
    route = docs("HTTPRoute", rollback_resources())[0]
    assert PLUGIN_NAME not in plugin_annotation_list(route)


def test_goal008_governance_allows_response_transformer_and_denies_request_transformer():
    policy = load_goal008_policy()
    assert PLUGIN_TYPE in set(policy["allowed_plugin_types"])
    assert "request-transformer" in set(policy["denied_plugin_types"])


def test_unsafe_request_transformer_fixture_fails_validation():
    unsafe = unsafe_request_transformer_fixture()
    assert unsafe[0]["plugin"] == "request-transformer"
    errors = validate_docs(unsafe, require_route=False)
    assert any("request-transformer" in error for error in errors)


def test_goal009_validator_passes():
    assert validate() == []
