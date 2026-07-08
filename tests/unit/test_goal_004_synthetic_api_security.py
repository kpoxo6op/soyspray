from scripts.goal004_security_config import APIS, CLIENT_FOR_API, CLIENTS, ROOT, api_access_group, api_auth_plugin, api_plugin_annotation, api_rate_limit_per_second, key_auth_secret_name, jwt_secret_name, acl_secret_name
from scripts.render_goal004_security_controls import render


def docs(kind):
    return [doc for doc in render() if doc.get("kind") == kind]


def test_routes_attach_goal004_kong_plugins():
    routes = {route["metadata"]["name"]: route for route in docs("HTTPRoute")}
    for api in APIS:
        route = routes[f"banklab-{api.key}"]
        assert route["metadata"]["annotations"]["konghq.com/plugins"] == api_plugin_annotation(api.key)


def test_kong_plugins_are_declared_per_api_namespace():
    plugins = {(plugin["metadata"]["namespace"], plugin["metadata"]["name"]): plugin for plugin in docs("KongPlugin")}
    for api in APIS:
        auth_name = "banklab-jwt" if api_auth_plugin(api.key) == "jwt" else "banklab-key-auth"
        auth = plugins[(api.namespace, auth_name)]
        acl = plugins[(api.namespace, "banklab-acl")]
        rate = plugins[(api.namespace, "banklab-rate-limit")]
        correlation = plugins[(api.namespace, "banklab-correlation-id")]
        assert auth["plugin"] == api_auth_plugin(api.key)
        assert acl["plugin"] == "acl"
        assert acl["config"]["allow"] == [api_access_group(api.key)]
        assert rate["plugin"] == "rate-limiting"
        assert rate["config"]["policy"] == "redis"
        assert rate["config"]["limit_by"] == "consumer"
        assert rate["config"]["second"] == api_rate_limit_per_second(api.exposure)
        assert correlation["plugin"] == "correlation-id"
        assert correlation["config"]["header_name"] == "X-Banklab-Correlation-ID"


def test_kong_consumers_reference_runtime_generated_credentials_only():
    consumers = {consumer["username"]: consumer for consumer in docs("KongConsumer")}
    assert set(consumers) == set(CLIENTS)
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        expected_auth_secret = jwt_secret_name(client) if api_auth_plugin(api.key) == "jwt" else key_auth_secret_name(client)
        assert consumers[client]["metadata"]["namespace"] == "synthetic-clients"
        assert consumers[client]["credentials"] == [expected_auth_secret, acl_secret_name(client, api.key)]


def test_static_security_validator_passes():
    from scripts.validate_goal004_security_controls import validate

    assert validate() == []
