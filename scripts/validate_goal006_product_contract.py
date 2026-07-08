#!/usr/bin/env python3
"""Validate the goal006 self-service product contract."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from scripts.goal006_product_contract_config import (
        API_ID,
        CONTRACT_PATH,
        DECK_STATE_PATH,
        GOAL_LABEL,
        HEADER_NAME,
        HEADER_VALUE,
        NAMESPACE,
        PLUGIN_NAME,
        PLUGIN_TYPE,
        PRODUCT_ID,
        REQUIRED_BASE_PLUGINS,
        ROUTE_NAME,
        TENANT_ID,
        api_product,
        load_deck_state,
        load_product_contract,
        tenant,
    )
    from scripts.render_goal006_product_contract import render, rollback_resources
except ModuleNotFoundError:
    from goal006_product_contract_config import (
        API_ID,
        CONTRACT_PATH,
        DECK_STATE_PATH,
        GOAL_LABEL,
        HEADER_NAME,
        HEADER_VALUE,
        NAMESPACE,
        PLUGIN_NAME,
        PLUGIN_TYPE,
        PRODUCT_ID,
        REQUIRED_BASE_PLUGINS,
        ROUTE_NAME,
        TENANT_ID,
        api_product,
        load_deck_state,
        load_product_contract,
        tenant,
    )
    from render_goal006_product_contract import render, rollback_resources


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def rendered_by_kind(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc.get("kind") == kind]


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def validate() -> list[str]:
    errors: list[str] = []
    contract = load_product_contract()
    deck = load_deck_state()
    product = api_product()
    owner = tenant()

    require(contract.get("product_id") == PRODUCT_ID, errors, "contract product_id mismatch")
    require(contract.get("api_id") == API_ID, errors, "contract must target existing accounts API")
    require(contract.get("tenant_id") == TENANT_ID, errors, "contract must target retail-accounts tenant")
    require(API_ID in owner.owned_api_ids, errors, "tenant must own contract API")
    require(contract.get("namespace") == product.namespace == NAMESPACE, errors, "contract namespace mismatch")
    require(contract.get("oss_enforcement", {}).get("plugin_type") == PLUGIN_TYPE, errors, "contract must use response-transformer")
    require(
        contract.get("runtime_marker", {}).get("header") == HEADER_NAME
        and contract.get("runtime_marker", {}).get("value") == HEADER_VALUE,
        errors,
        "runtime marker mismatch",
    )
    require(contract.get("change_class") == "standard", errors, "contract must be a standard change")

    services = deck.get("services", [])
    plugins = deck.get("plugins", [])
    require(deck.get("_format_version") == "3.0", errors, "deck state must use format version 3.0")
    require(len(services) == 1 and services[0].get("name") == product.kong_service_name, errors, "deck service mismatch")
    routes = services[0].get("routes", []) if services else []
    require(len(routes) == 1 and routes[0].get("name") == ROUTE_NAME, errors, "deck route mismatch")
    require(len(plugins) == 1 and plugins[0].get("name") == PLUGIN_TYPE, errors, "deck plugin mismatch")
    require(f"{HEADER_NAME}:{HEADER_VALUE}" in plugins[0].get("config", {}).get("add", {}).get("headers", []), errors, "deck header mismatch")
    require(GOAL_LABEL in deck.get("_info", {}).get("select_tags", []), errors, "deck select_tags must include goal-006")

    for path in (CONTRACT_PATH, DECK_STATE_PATH):
        content = text(path)
        require("konnect" not in content, errors, f"{path} must not require Konnect")
        require("enterprise" not in content, errors, f"{path} must not require Enterprise features")

    docs = render()
    require(len(rendered_by_kind(docs, "KongPlugin")) == 1, errors, "render must produce one KongPlugin")
    require(len(rendered_by_kind(docs, "HTTPRoute")) == 1, errors, "render must produce one HTTPRoute")
    require(not rendered_by_kind(docs, "Secret"), errors, "goal006 must not render Secrets")
    require(not rendered_by_kind(docs, "KongClusterPlugin"), errors, "goal006 must not render KongClusterPlugins")

    plugin = rendered_by_kind(docs, "KongPlugin")[0]
    route = rendered_by_kind(docs, "HTTPRoute")[0]
    require(plugin["metadata"]["name"] == PLUGIN_NAME, errors, "rendered plugin name mismatch")
    require(plugin["metadata"]["namespace"] == NAMESPACE, errors, "rendered plugin namespace mismatch")
    require(plugin["plugin"] == PLUGIN_TYPE, errors, "rendered plugin type mismatch")
    require(f"{HEADER_NAME}:{HEADER_VALUE}" in plugin["config"]["add"]["headers"], errors, "rendered plugin header mismatch")
    require(route["metadata"]["name"] == ROUTE_NAME, errors, "rendered route name mismatch")
    plugins_annotation = route["metadata"]["annotations"]["konghq.com/plugins"].split(",")
    for base_plugin in REQUIRED_BASE_PLUGINS:
        require(base_plugin in plugins_annotation, errors, f"rendered route missing base plugin {base_plugin}")
    require(plugins_annotation[-1] == PLUGIN_NAME, errors, "goal006 plugin must be appended after existing route plugins")
    require(route["metadata"]["labels"].get("platform.soyspray.io/product-id") == PRODUCT_ID, errors, "route missing product-id label")

    rollback = rollback_resources()
    rollback_route = rendered_by_kind(rollback, "HTTPRoute")[0]
    require(PLUGIN_NAME not in rollback_route["metadata"]["annotations"]["konghq.com/plugins"], errors, "rollback route must omit goal006 plugin")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"goal006 validation failed: {error}", file=sys.stderr)
        return 1
    print("goal006 product contract validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
