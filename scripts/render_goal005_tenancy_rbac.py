#!/usr/bin/env python3
"""Render stable goal005 tenancy and RBAC resources."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from typing import Any

import yaml

try:
    from scripts.goal004_security_config import APIS
    from scripts.render_goal004_security_controls import render as render_goal004
    from scripts.goal005_tenancy_config import (
        CATALOG_CONFIGMAP,
        GOAL005_LABEL_PREFIX,
        PLATFORM_NAMESPACE,
        PLATFORM_ROLE_BINDING_NAME,
        PLATFORM_ROLE_NAME,
        PLATFORM_SERVICE_ACCOUNT,
        TENANT_ROLE_BINDING_NAME,
        TENANT_ROLE_NAME,
        TENANT_SERVICE_ACCOUNTS,
        load_api_products,
        load_tenants,
        products_by_id,
    )
except ModuleNotFoundError:
    from goal004_security_config import APIS
    from render_goal004_security_controls import render as render_goal004
    from goal005_tenancy_config import (
        CATALOG_CONFIGMAP,
        GOAL005_LABEL_PREFIX,
        PLATFORM_NAMESPACE,
        PLATFORM_ROLE_BINDING_NAME,
        PLATFORM_ROLE_NAME,
        PLATFORM_SERVICE_ACCOUNT,
        TENANT_ROLE_BINDING_NAME,
        TENANT_ROLE_NAME,
        TENANT_SERVICE_ACCOUNTS,
        load_api_products,
        load_tenants,
        products_by_id,
    )


def base_labels(tenant_id: str | None = None, api_id: str | None = None, product: Any | None = None) -> dict[str, str]:
    labels = {
        f"{GOAL005_LABEL_PREFIX}/managed-by": "gitops",
        f"{GOAL005_LABEL_PREFIX}/goal": "goal-005",
    }
    if tenant_id:
        labels[f"{GOAL005_LABEL_PREFIX}/tenant"] = tenant_id
    if api_id:
        labels[f"{GOAL005_LABEL_PREFIX}/api-id"] = api_id
    if product:
        labels.update(
            {
                f"{GOAL005_LABEL_PREFIX}/logical-workspace": product.logical_workspace,
                f"{GOAL005_LABEL_PREFIX}/exposure": product.exposure,
                f"{GOAL005_LABEL_PREFIX}/data-classification": product.data_classification,
                f"{GOAL005_LABEL_PREFIX}/change-class": "standard",
            }
        )
    return labels


def annotate(doc: dict[str, Any], product: Any, tenant_id: str, change_class: str = "standard") -> dict[str, Any]:
    patched = deepcopy(doc)
    metadata = patched.setdefault("metadata", {})
    metadata.setdefault("labels", {}).update(base_labels(tenant_id, product.api_id, product))
    metadata["labels"][f"{GOAL005_LABEL_PREFIX}/change-class"] = change_class
    metadata.setdefault("annotations", {}).update(
        {
            f"{GOAL005_LABEL_PREFIX}/runbook": product.runbook,
            f"{GOAL005_LABEL_PREFIX}/docs-owner": product.docs_owner,
        }
    )
    return patched


def namespaces() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    tenants = load_tenants()
    products = products_by_id()
    namespace_owners: dict[str, tuple[str, Any]] = {}
    for tenant in tenants:
        for api_id in tenant.owned_api_ids:
            product = products[api_id]
            namespace_owners[product.namespace] = (tenant.tenant_id, product)
    for namespace_name in sorted(namespace_owners):
        tenant_id, product = namespace_owners[namespace_name]
        docs.append(
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": namespace_name,
                    "labels": base_labels(tenant_id, product.api_id, product),
                    "annotations": {f"{GOAL005_LABEL_PREFIX}/runbook": product.runbook},
                },
            }
        )
    return docs


def serviceaccounts() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for tenant in load_tenants():
        docs.append(
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": {
                    "name": TENANT_SERVICE_ACCOUNTS[tenant.tenant_id],
                    "namespace": tenant.namespace,
                    "labels": base_labels(tenant.tenant_id),
                },
            }
        )
    docs.append(
        {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": PLATFORM_SERVICE_ACCOUNT,
                "namespace": PLATFORM_NAMESPACE,
                "labels": base_labels("kong-platform"),
            },
        }
    )
    return docs


def tenant_role(namespace: str, tenant_id: str) -> dict[str, Any]:
    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "Role",
        "metadata": {"name": TENANT_ROLE_NAME, "namespace": namespace, "labels": base_labels(tenant_id)},
        "rules": [
            {"apiGroups": [""], "resources": ["services"], "verbs": ["get", "list", "watch", "create", "update", "patch"]},
            {
                "apiGroups": ["gateway.networking.k8s.io"],
                "resources": ["httproutes"],
                "verbs": ["get", "list", "watch", "create", "update", "patch"],
            },
            {
                "apiGroups": ["configuration.konghq.com"],
                "resources": ["kongplugins"],
                "verbs": ["get", "list", "watch", "create", "update", "patch"],
            },
        ],
    }


def roles() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for tenant in load_tenants():
        for namespace in tenant.api_namespaces:
            docs.append(tenant_role(namespace, tenant.tenant_id))
    docs.append(
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": {"name": PLATFORM_ROLE_NAME, "namespace": PLATFORM_NAMESPACE, "labels": base_labels("kong-platform")},
            "rules": [{"apiGroups": [""], "resources": ["configmaps"], "verbs": ["get", "list", "watch"]}],
        }
    )
    return docs


def rolebindings() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for tenant in load_tenants():
        for namespace in tenant.api_namespaces:
            docs.append(
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "RoleBinding",
                    "metadata": {"name": TENANT_ROLE_BINDING_NAME, "namespace": namespace, "labels": base_labels(tenant.tenant_id)},
                    "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": TENANT_ROLE_NAME},
                    "subjects": [
                        {
                            "kind": "ServiceAccount",
                            "name": TENANT_SERVICE_ACCOUNTS[tenant.tenant_id],
                            "namespace": tenant.namespace,
                        }
                    ],
                }
            )
    docs.append(
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": PLATFORM_ROLE_BINDING_NAME, "namespace": PLATFORM_NAMESPACE, "labels": base_labels("kong-platform")},
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": PLATFORM_ROLE_NAME},
            "subjects": [{"kind": "ServiceAccount", "name": PLATFORM_SERVICE_ACCOUNT, "namespace": PLATFORM_NAMESPACE}],
        }
    )
    return docs


def catalog_configmap() -> dict[str, Any]:
    tenants = load_tenants()
    products = load_api_products()
    tenant_summary = [
        {
            "tenant_id": tenant.tenant_id,
            "logical_workspace": tenant.logical_workspace,
            "namespace": tenant.namespace,
            "api_namespaces": list(tenant.api_namespaces),
            "owned_api_ids": list(tenant.owned_api_ids),
        }
        for tenant in tenants
    ]
    product_summary = [
        {
            "api_id": product.api_id,
            "tenant_id": product.tenant_id,
            "namespace": product.namespace,
            "exposure": product.exposure,
            "data_classification": product.data_classification,
            "credential_owner": product.credential_owner,
        }
        for product in products
    ]
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": CATALOG_CONFIGMAP, "namespace": PLATFORM_NAMESPACE, "labels": base_labels("kong-platform")},
        "data": {
            "tenants.json": json.dumps(tenant_summary, sort_keys=True),
            "api-products.json": json.dumps(product_summary, sort_keys=True),
        },
    }


def ownership_resources() -> list[dict[str, Any]]:
    goal004_docs = render_goal004()
    products = products_by_id()
    tenants = {api_id: tenant.tenant_id for tenant in load_tenants() for api_id in tenant.owned_api_ids}
    docs: list[dict[str, Any]] = []
    kong_kinds = {"HTTPRoute", "KongPlugin"}
    for doc in goal004_docs:
        if doc.get("kind") not in kong_kinds:
            continue
        namespace = doc.get("metadata", {}).get("namespace")
        api_id = None
        for api in APIS:
            if namespace == api.namespace:
                api_id = api.key
                break
        if not api_id:
            continue
        docs.append(annotate(doc, products[api_id], tenants[api_id]))
    return docs


def render() -> list[dict[str, Any]]:
    return [
        *namespaces(),
        *serviceaccounts(),
        *roles(),
        *rolebindings(),
        catalog_configmap(),
        *ownership_resources(),
    ]


def main() -> int:
    yaml.safe_dump_all(render(), sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
