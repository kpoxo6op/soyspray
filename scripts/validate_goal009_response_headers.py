#!/usr/bin/env python3
"""Validate goal009 governed response-header resources."""

from __future__ import annotations

import sys
from typing import Any

try:
    from scripts.goal008_governance_policy_config import load_policy as load_goal008_policy
    from scripts.goal009_response_headers_config import (
        API_ID,
        FORBIDDEN_PLUGIN_TYPES,
        GOAL_ID,
        GOAL_LABEL,
        NAMESPACE,
        PLUGIN_NAME,
        PLUGIN_TYPE,
        REQUIRED_BASE_PLUGINS,
        REQUIRED_HEADER_LINES,
        ROLLBACK_RUNBOOK,
        ROUTE_NAME,
        TENANT_ID,
    )
    from scripts.render_goal009_response_headers import render, rollback_resources, stable_accounts_route, unsafe_request_transformer_fixture
except ModuleNotFoundError:
    from goal008_governance_policy_config import load_policy as load_goal008_policy
    from goal009_response_headers_config import (
        API_ID,
        FORBIDDEN_PLUGIN_TYPES,
        GOAL_ID,
        GOAL_LABEL,
        NAMESPACE,
        PLUGIN_NAME,
        PLUGIN_TYPE,
        REQUIRED_BASE_PLUGINS,
        REQUIRED_HEADER_LINES,
        ROLLBACK_RUNBOOK,
        ROUTE_NAME,
        TENANT_ID,
    )
    from render_goal009_response_headers import render, rollback_resources, stable_accounts_route, unsafe_request_transformer_fixture


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def rendered_by_kind(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc.get("kind") == kind]


def plugin_annotation_list(route: dict[str, Any]) -> list[str]:
    annotation = route.get("metadata", {}).get("annotations", {}).get("konghq.com/plugins", "")
    return [plugin.strip() for plugin in annotation.split(",") if plugin.strip()]


def validate_docs(docs: list[dict[str, Any]], require_route: bool = True) -> list[str]:
    errors: list[str] = []
    plugins = rendered_by_kind(docs, "KongPlugin")
    cluster_plugins = rendered_by_kind(docs, "KongClusterPlugin")
    routes = rendered_by_kind(docs, "HTTPRoute")

    require(len(plugins) == 1, errors, "render must produce one KongPlugin")
    require(not cluster_plugins, errors, "goal009 must not render KongClusterPlugins")
    require(not rendered_by_kind(docs, "Secret"), errors, "goal009 must not render Secrets")
    if require_route:
        require(len(routes) == 1, errors, "render must produce one HTTPRoute")

    for plugin in plugins + cluster_plugins:
        plugin_type = plugin.get("plugin")
        require(plugin_type == PLUGIN_TYPE, errors, f"plugin type must be {PLUGIN_TYPE}")
        require(plugin_type not in FORBIDDEN_PLUGIN_TYPES, errors, f"unsafe plugin type {plugin_type} must not be rendered")
        require(plugin.get("metadata", {}).get("namespace") == NAMESPACE, errors, "KongPlugin must stay tenant namespaced")

    if plugins:
        plugin = plugins[0]
        metadata = plugin.get("metadata", {})
        require(metadata.get("name") == PLUGIN_NAME, errors, "rendered plugin name mismatch")
        require(metadata.get("namespace") == NAMESPACE, errors, "rendered plugin namespace mismatch")
        require(plugin.get("plugin") == PLUGIN_TYPE, errors, "rendered plugin type mismatch")
        require(metadata.get("labels", {}).get("platform.soyspray.io/goal") == GOAL_LABEL, errors, "plugin missing goal label")
        require(metadata.get("annotations", {}).get("platform.soyspray.io/runbook") == ROLLBACK_RUNBOOK, errors, "plugin runbook annotation mismatch")
        headers = plugin.get("config", {}).get("add", {}).get("headers", [])
        for header in REQUIRED_HEADER_LINES:
            require(header in headers, errors, f"rendered plugin missing header {header}")
        require(len(headers) == len(REQUIRED_HEADER_LINES), errors, "rendered plugin must add only the required headers")

    if routes:
        route = routes[0]
        require(route.get("metadata", {}).get("name") == ROUTE_NAME, errors, "rendered route name mismatch")
        require(route.get("metadata", {}).get("namespace") == NAMESPACE, errors, "rendered route namespace mismatch")
        route_plugins = plugin_annotation_list(route)
        base_route_plugins = plugin_annotation_list(stable_accounts_route())
        require(route_plugins[: len(base_route_plugins)] == base_route_plugins, errors, "route must preserve existing plugin annotation order")
        for base_plugin in REQUIRED_BASE_PLUGINS:
            require(base_plugin in route_plugins, errors, f"rendered route missing base plugin {base_plugin}")
        require(route_plugins.count(PLUGIN_NAME) == 1, errors, "route must attach goal009 plugin exactly once")
        require(route_plugins[-1] == PLUGIN_NAME, errors, "goal009 plugin must be appended after existing route plugins")
        require(route.get("metadata", {}).get("labels", {}).get("platform.soyspray.io/api-id") == API_ID, errors, "route missing api-id label")
        require(route.get("metadata", {}).get("labels", {}).get("platform.soyspray.io/tenant") == TENANT_ID, errors, "route missing tenant label")

    return errors


def validate() -> list[str]:
    errors = validate_docs(render())

    rollback = rollback_resources()
    rollback_plugins = rendered_by_kind(rollback, "KongPlugin")
    rollback_routes = rendered_by_kind(rollback, "HTTPRoute")
    require(not rollback_plugins, errors, "rollback render must not include the goal009 KongPlugin")
    require(len(rollback_routes) == 1, errors, "rollback render must include one stable HTTPRoute")
    if rollback_routes:
        rollback_route_plugins = plugin_annotation_list(rollback_routes[0])
        require(PLUGIN_NAME not in rollback_route_plugins, errors, "rollback route must omit goal009 plugin")
        for base_plugin in REQUIRED_BASE_PLUGINS:
            require(base_plugin in rollback_route_plugins, errors, f"rollback route missing base plugin {base_plugin}")

    policy = load_goal008_policy()
    allowed_plugins = set(policy.get("allowed_plugin_types", []))
    denied_plugins = set(policy.get("denied_plugin_types", []))
    require(PLUGIN_TYPE in allowed_plugins, errors, "goal009 plugin type must be allowed by goal008 governance")
    require("request-transformer" in denied_plugins, errors, "goal008 governance must deny request-transformer")
    require(PLUGIN_TYPE not in denied_plugins, errors, "goal009 plugin type must not be denied by goal008 governance")

    unsafe_errors = validate_docs(unsafe_request_transformer_fixture(), require_route=False)
    require(any("request-transformer" in error for error in unsafe_errors), errors, "unsafe request-transformer fixture must fail validation")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"goal009 validation failed: {error}", file=sys.stderr)
        return 1
    print("goal009 response header validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
