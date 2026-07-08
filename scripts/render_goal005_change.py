#!/usr/bin/env python3
"""Render the goal005 sample normal change resources."""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from typing import Any

import yaml

try:
    from scripts.goal005_tenancy_config import (
        SAMPLE_CHANGE_API_ID,
        SAMPLE_CHANGE_HEADER,
        SAMPLE_CHANGE_HEADER_VALUE,
        SAMPLE_CHANGE_ID,
        SAMPLE_CHANGE_PLUGIN_NAME,
        SAMPLE_CHANGE_PLUGIN_TYPE,
        products_by_id,
        sample_change,
    )
    from scripts.render_goal005_tenancy_rbac import GOAL005_LABEL_PREFIX, annotate, ownership_resources
except ModuleNotFoundError:
    from goal005_tenancy_config import (
        SAMPLE_CHANGE_API_ID,
        SAMPLE_CHANGE_HEADER,
        SAMPLE_CHANGE_HEADER_VALUE,
        SAMPLE_CHANGE_ID,
        SAMPLE_CHANGE_PLUGIN_NAME,
        SAMPLE_CHANGE_PLUGIN_TYPE,
        products_by_id,
        sample_change,
    )
    from render_goal005_tenancy_rbac import GOAL005_LABEL_PREFIX, annotate, ownership_resources


def route_with_sample_plugin(product: Any, tenant_id: str) -> dict[str, Any]:
    routes = [
        doc
        for doc in ownership_resources()
        if doc.get("kind") == "HTTPRoute" and doc.get("metadata", {}).get("name") in product.kong_route_names
    ]
    if len(routes) != 1:
        raise ValueError(f"expected exactly one route for {product.api_id}, found {len(routes)}")
    route = annotate(routes[0], product, tenant_id, "normal")
    annotations = route.setdefault("metadata", {}).setdefault("annotations", {})
    plugins = [plugin.strip() for plugin in annotations.get("konghq.com/plugins", "").split(",") if plugin.strip()]
    if SAMPLE_CHANGE_PLUGIN_NAME not in plugins:
        plugins.append(SAMPLE_CHANGE_PLUGIN_NAME)
    annotations["konghq.com/plugins"] = ",".join(plugins)
    return route


def sample_plugin(product: Any, tenant_id: str) -> dict[str, Any]:
    doc = {
        "apiVersion": "configuration.konghq.com/v1",
        "kind": "KongPlugin",
        "metadata": {
            "name": SAMPLE_CHANGE_PLUGIN_NAME,
            "namespace": product.namespace,
            "annotations": {
                "kubernetes.io/ingress.class": "kong",
                f"{GOAL005_LABEL_PREFIX}/runbook": "docs/runbooks/goal-005-change-rollback.md",
            },
            "labels": {
                f"{GOAL005_LABEL_PREFIX}/tenant": tenant_id,
                f"{GOAL005_LABEL_PREFIX}/api-id": product.api_id,
                f"{GOAL005_LABEL_PREFIX}/logical-workspace": product.logical_workspace,
                f"{GOAL005_LABEL_PREFIX}/exposure": product.exposure,
                f"{GOAL005_LABEL_PREFIX}/data-classification": product.data_classification,
                f"{GOAL005_LABEL_PREFIX}/managed-by": "gitops",
                f"{GOAL005_LABEL_PREFIX}/goal": "goal-005",
                f"{GOAL005_LABEL_PREFIX}/change-class": "normal",
            },
        },
        "plugin": SAMPLE_CHANGE_PLUGIN_TYPE,
        "config": {"add": {"headers": [f"{SAMPLE_CHANGE_HEADER}:{SAMPLE_CHANGE_HEADER_VALUE}"]}},
    }
    return doc


def render(plugin_only: bool = False) -> list[dict[str, Any]]:
    change = sample_change()
    product = products_by_id()[SAMPLE_CHANGE_API_ID]
    tenant_id = change["tenant_id"]
    plugin = sample_plugin(product, tenant_id)
    if plugin_only:
        return [plugin]
    return [plugin, route_with_sample_plugin(product, tenant_id)]


def rollback_resources() -> list[dict[str, Any]]:
    product = products_by_id()[SAMPLE_CHANGE_API_ID]
    route = None
    for doc in ownership_resources():
        if doc.get("kind") == "HTTPRoute" and doc.get("metadata", {}).get("name") in product.kong_route_names:
            route = deepcopy(doc)
            break
    if route is None:
        raise ValueError(f"missing route for rollback: {SAMPLE_CHANGE_API_ID}")
    return [route]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-only", action="store_true", help="render only the sample KongPlugin, for kubectl delete")
    parser.add_argument("--rollback", action="store_true", help="render stable resources that remove the sample route annotation")
    args = parser.parse_args()
    docs = rollback_resources() if args.rollback else render(plugin_only=args.plugin_only)
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
