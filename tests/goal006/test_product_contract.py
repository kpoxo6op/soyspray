from scripts.goal006_product_contract_config import (
    API_ID,
    HEADER_NAME,
    HEADER_VALUE,
    NAMESPACE,
    PLUGIN_NAME,
    PLUGIN_TYPE,
    PRODUCT_ID,
    REQUIRED_BASE_PLUGINS,
    ROUTE_NAME,
    TENANT_ID,
    load_deck_state,
    load_product_contract,
)
from scripts.goal005_tenancy_config import load_api_products, load_tenants
from scripts.render_goal006_product_contract import render, rollback_resources
from scripts.validate_goal006_product_contract import validate


def docs(kind):
    return [doc for doc in render() if doc.get("kind") == kind]


def test_contract_references_existing_api_and_tenant():
    contract = load_product_contract()
    assert contract["product_id"] == PRODUCT_ID
    assert contract["api_id"] == API_ID
    assert contract["tenant_id"] == TENANT_ID
    assert contract["namespace"] == NAMESPACE
    assert API_ID in {product.api_id for product in load_api_products()}
    assert TENANT_ID in {tenant.tenant_id for tenant in load_tenants()}


def test_contract_does_not_create_new_api():
    contract = load_product_contract()
    catalog_products = {product.api_id for product in load_api_products()}
    assert set(catalog_products) == {
        "accounts",
        "cards",
        "customer-profile",
        "fraud-decisions",
        "open-banking",
        "payments",
    }
    assert contract["api_id"] in catalog_products


def test_deck_state_tracks_the_same_product_contract():
    deck = load_deck_state()
    assert deck["_format_version"] == "3.0"
    assert PRODUCT_ID in deck["_info"]["select_tags"]
    service = deck["services"][0]
    assert service["name"] == "banklab-accounts-api"
    assert service["routes"][0]["name"] == ROUTE_NAME
    plugin = deck["plugins"][0]
    assert plugin["name"] == PLUGIN_TYPE
    assert f"{HEADER_NAME}:{HEADER_VALUE}" in plugin["config"]["add"]["headers"]


def test_rendered_product_contract_is_namespaced_and_oss_only():
    rendered = render()
    assert [doc for doc in rendered if doc.get("kind") == "KongPlugin"]
    assert [doc for doc in rendered if doc.get("kind") == "HTTPRoute"]
    assert not [doc for doc in rendered if doc.get("kind") == "Secret"]
    assert not [doc for doc in rendered if doc.get("kind") == "KongClusterPlugin"]
    plugin = docs("KongPlugin")[0]
    assert plugin["metadata"]["namespace"] == NAMESPACE
    assert plugin["plugin"] == PLUGIN_TYPE


def test_route_preserves_goal004_plugins_and_appends_product_plugin():
    route = docs("HTTPRoute")[0]
    assert route["metadata"]["name"] == ROUTE_NAME
    plugins = route["metadata"]["annotations"]["konghq.com/plugins"].split(",")
    for base_plugin in REQUIRED_BASE_PLUGINS:
        assert base_plugin in plugins
    assert plugins[-1] == PLUGIN_NAME
    assert route["metadata"]["labels"]["platform.soyspray.io/product-id"] == PRODUCT_ID


def test_plugin_adds_product_contract_header():
    plugin = docs("KongPlugin")[0]
    assert plugin["metadata"]["name"] == PLUGIN_NAME
    assert f"{HEADER_NAME}:{HEADER_VALUE}" in plugin["config"]["add"]["headers"]


def test_rollback_route_omits_goal006_plugin():
    route = [doc for doc in rollback_resources() if doc.get("kind") == "HTTPRoute"][0]
    assert PLUGIN_NAME not in route["metadata"]["annotations"]["konghq.com/plugins"].split(",")


def test_goal006_validator_passes():
    assert validate() == []
