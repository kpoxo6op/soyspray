#!/usr/bin/env python3
"""Render goal006 product contract resources."""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from typing import Any

import yaml

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
        ROLLBACK_RUNBOOK,
        ROUTE_NAME,
        TENANT_ID,
        api_product,
        relative,
    )
    from scripts.render_goal005_tenancy_rbac import annotate, ownership_resources
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
        ROLLBACK_RUNBOOK,
        ROUTE_NAME,
        TENANT_ID,
        api_product,
        relative,
    )
    from render_goal005_tenancy_rbac import annotate, ownership_resources


LABEL_PREFIX = "platform.soyspray.io"


def product_labels() -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}/tenant": TENANT_ID,
        f"{LABEL_PREFIX}/api-id": API_ID,
        f"{LABEL_PREFIX}/product-id": PRODUCT_ID,
        f"{LABEL_PREFIX}/managed-by": "gitops",
        f"{LABEL_PREFIX}/goal": GOAL_LABEL,
        f"{LABEL_PREFIX}/change-class": "standard",
    }


def product_annotations() -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}/runbook": ROLLBACK_RUNBOOK,
        f"{LABEL_PREFIX}/product-contract-file": relative(CONTRACT_PATH),
        f"{LABEL_PREFIX}/deck-state-file": relative(DECK_STATE_PATH),
    }


def product_plugin() -> dict[str, Any]:
    product = api_product()
    labels = product_labels()
    labels.update(
        {
            f"{LABEL_PREFIX}/logical-workspace": product.logical_workspace,
            f"{LABEL_PREFIX}/exposure": product.exposure,
            f"{LABEL_PREFIX}/data-classification": product.data_classification,
        }
    )
    return {
        "apiVersion": "configuration.konghq.com/v1",
        "kind": "KongPlugin",
        "metadata": {
            "name": PLUGIN_NAME,
            "namespace": NAMESPACE,
            "annotations": {
                "kubernetes.io/ingress.class": "kong",
                **product_annotations(),
            },
            "labels": labels,
        },
        "plugin": PLUGIN_TYPE,
        "config": {"add": {"headers": [f"{HEADER_NAME}:{HEADER_VALUE}"]}},
    }


def stable_accounts_route() -> dict[str, Any]:
    product = api_product()
    for doc in ownership_resources():
        if doc.get("kind") == "HTTPRoute" and doc.get("metadata", {}).get("name") == ROUTE_NAME:
            return annotate(doc, product, TENANT_ID, "standard")
    raise ValueError(f"missing HTTPRoute/{NAMESPACE}/{ROUTE_NAME}")


def route_with_product_plugin() -> dict[str, Any]:
    route = deepcopy(stable_accounts_route())
    metadata = route.setdefault("metadata", {})
    metadata.setdefault("labels", {}).update(product_labels())
    metadata.setdefault("annotations", {}).update(product_annotations())
    annotations = metadata["annotations"]
    plugins = [plugin.strip() for plugin in annotations.get("konghq.com/plugins", "").split(",") if plugin.strip()]
    if PLUGIN_NAME not in plugins:
        plugins.append(PLUGIN_NAME)
    annotations["konghq.com/plugins"] = ",".join(plugins)
    return route


def render(plugin_only: bool = False) -> list[dict[str, Any]]:
    plugin = product_plugin()
    if plugin_only:
        return [plugin]
    return [plugin, route_with_product_plugin()]


def rollback_resources() -> list[dict[str, Any]]:
    return [stable_accounts_route()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-only", action="store_true", help="render only the goal006 KongPlugin for deletion")
    parser.add_argument("--rollback", action="store_true", help="render stable route resources without the goal006 plugin")
    args = parser.parse_args()
    docs = rollback_resources() if args.rollback else render(plugin_only=args.plugin_only)
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
