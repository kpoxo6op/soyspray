#!/usr/bin/env python3
"""Validate goal005 rendered Kubernetes ownership and RBAC manifests."""

from __future__ import annotations

import sys
from typing import Any

try:
    from scripts.goal005_tenancy_config import (
        GOAL005_LABEL_PREFIX,
        PLATFORM_NAMESPACE,
        SAMPLE_CHANGE_PLUGIN_NAME,
        TENANT_ROLE_NAME,
        TENANT_SERVICE_ACCOUNTS,
        load_tenants,
        products_by_id,
    )
    from scripts.render_goal005_change import render as render_change
    from scripts.render_goal005_tenancy_rbac import render as render_tenancy
except ModuleNotFoundError:
    from goal005_tenancy_config import (
        GOAL005_LABEL_PREFIX,
        PLATFORM_NAMESPACE,
        SAMPLE_CHANGE_PLUGIN_NAME,
        TENANT_ROLE_NAME,
        TENANT_SERVICE_ACCOUNTS,
        load_tenants,
        products_by_id,
    )
    from render_goal005_change import render as render_change
    from render_goal005_tenancy_rbac import render as render_tenancy


KONG_FACING_KINDS = {"HTTPRoute", "KongPlugin"}
FORBIDDEN_TENANT_KINDS = {"Secret", "KongClusterPlugin", "NetworkPolicy"}
ADMIN_MARKERS = {"kong-admin", "gateway-admin", "admin-api", "banklab-kong-gateway-admin"}


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def all_docs() -> list[dict[str, Any]]:
    return [*render_tenancy(), *render_change()]


def has_owner_metadata(doc: dict[str, Any]) -> bool:
    metadata = doc.get("metadata", {})
    labels = metadata.get("labels", {})
    annotations = metadata.get("annotations", {})
    required_labels = {
        f"{GOAL005_LABEL_PREFIX}/tenant",
        f"{GOAL005_LABEL_PREFIX}/api-id",
        f"{GOAL005_LABEL_PREFIX}/logical-workspace",
        f"{GOAL005_LABEL_PREFIX}/exposure",
        f"{GOAL005_LABEL_PREFIX}/data-classification",
        f"{GOAL005_LABEL_PREFIX}/managed-by",
        f"{GOAL005_LABEL_PREFIX}/change-class",
    }
    return required_labels <= set(labels) and f"{GOAL005_LABEL_PREFIX}/runbook" in annotations


def validate_docs(errors: list[str]) -> None:
    docs = all_docs()
    require(render_tenancy(), errors, "goal005 tenancy overlay must render")
    require(render_change(), errors, "goal005 normal-change overlay must render")

    for doc in docs:
        kind = doc.get("kind")
        name = doc.get("metadata", {}).get("name", "")
        namespace = doc.get("metadata", {}).get("namespace")
        if kind in KONG_FACING_KINDS:
            require(has_owner_metadata(doc), errors, f"{kind}/{name} lacks ownership metadata")
            require(namespace, errors, f"{kind}/{name} must be namespaced")
        require(kind not in FORBIDDEN_TENANT_KINDS, errors, f"goal005 tenant resources must not create {kind}")
        lower_name = name.lower()
        require(not any(marker in lower_name for marker in ADMIN_MARKERS), errors, f"goal005 must not expose Kong Admin resources: {kind}/{name}")
        serialized = str(doc).lower()
        require("stringdata" not in serialized and "credential" not in lower_name, errors, f"goal005 rendered doc may reference credential Secret values: {kind}/{name}")


def validate_rbac(errors: list[str]) -> None:
    docs = render_tenancy()
    tenants = {tenant.tenant_id: tenant for tenant in load_tenants()}
    tenant_namespaces = {namespace: tenant.tenant_id for tenant in tenants.values() for namespace in tenant.api_namespaces}
    roles = [doc for doc in docs if doc.get("kind") == "Role" and doc.get("metadata", {}).get("name") == TENANT_ROLE_NAME]
    bindings = [doc for doc in docs if doc.get("kind") == "RoleBinding" and doc.get("metadata", {}).get("name") == "goal005-tenant-api-applier"]
    require(roles, errors, "tenant Roles must render")
    require(bindings, errors, "tenant RoleBindings must render")
    for role in roles:
        namespace = role["metadata"]["namespace"]
        tenant_id = role["metadata"]["labels"][f"{GOAL005_LABEL_PREFIX}/tenant"]
        require(tenant_namespaces.get(namespace) == tenant_id, errors, f"Role {namespace}/{TENANT_ROLE_NAME} is outside tenant scope")
        for rule in role.get("rules", []):
            resources = set(rule.get("resources", []))
            require("secrets" not in resources, errors, f"Role {namespace}/{TENANT_ROLE_NAME} grants Secret access")
            require("networkpolicies" not in resources, errors, f"Role {namespace}/{TENANT_ROLE_NAME} grants NetworkPolicy access")
            require("kongclusterplugins" not in resources, errors, f"Role {namespace}/{TENANT_ROLE_NAME} grants KongClusterPlugin access")
    for binding in bindings:
        namespace = binding["metadata"]["namespace"]
        tenant_id = binding["metadata"]["labels"][f"{GOAL005_LABEL_PREFIX}/tenant"]
        subjects = binding.get("subjects", [])
        require(len(subjects) == 1, errors, f"RoleBinding {namespace} must bind exactly one tenant service account")
        subject = subjects[0]
        tenant = tenants[tenant_id]
        require(subject.get("name") == TENANT_SERVICE_ACCOUNTS[tenant_id], errors, f"RoleBinding {namespace} binds wrong service account")
        require(subject.get("namespace") == tenant.namespace, errors, f"RoleBinding {namespace} binds service account from wrong namespace")
        require(namespace in tenant.api_namespaces, errors, f"RoleBinding {namespace} grants cross-tenant access")


def validate_change(errors: list[str]) -> None:
    docs = render_change()
    plugins = [doc for doc in docs if doc.get("kind") == "KongPlugin" and doc.get("metadata", {}).get("name") == SAMPLE_CHANGE_PLUGIN_NAME]
    routes = [doc for doc in docs if doc.get("kind") == "HTTPRoute"]
    require(len(plugins) == 1, errors, "sample change must render one KongPlugin")
    require(len(routes) == 1, errors, "sample change must render one HTTPRoute")
    if plugins:
        plugin = plugins[0]
        require(plugin.get("plugin") == "response-transformer", errors, "sample change must use response-transformer")
        require(plugin.get("metadata", {}).get("namespace"), errors, "sample change plugin must be namespaced")
    if routes:
        annotations = routes[0].get("metadata", {}).get("annotations", {})
        require(SAMPLE_CHANGE_PLUGIN_NAME in annotations.get("konghq.com/plugins", ""), errors, "sample change route must reference the sample plugin")


def validate() -> list[str]:
    errors: list[str] = []
    validate_docs(errors)
    validate_rbac(errors)
    validate_change(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Goal005 rendered ownership validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Goal005 rendered ownership validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
