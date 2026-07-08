#!/usr/bin/env python3
"""Render goal009 governed response-header resources."""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from typing import Any

import yaml

try:
    from scripts.goal009_response_headers_config import (
        API_ID,
        DOC_PATH,
        GOAL_LABEL,
        NAMESPACE,
        PLUGIN_NAME,
        PLUGIN_TYPE,
        REQUIRED_HEADER_LINES,
        ROLLBACK_RUNBOOK,
        ROUTE_NAME,
        TENANT_ID,
        relative,
    )
    from scripts.goal006_product_contract_config import api_product
    from scripts.render_goal005_tenancy_rbac import annotate, ownership_resources
except ModuleNotFoundError:
    from goal009_response_headers_config import (
        API_ID,
        DOC_PATH,
        GOAL_LABEL,
        NAMESPACE,
        PLUGIN_NAME,
        PLUGIN_TYPE,
        REQUIRED_HEADER_LINES,
        ROLLBACK_RUNBOOK,
        ROUTE_NAME,
        TENANT_ID,
        relative,
    )
    from goal006_product_contract_config import api_product
    from render_goal005_tenancy_rbac import annotate, ownership_resources


LABEL_PREFIX = "platform.soyspray.io"


def response_policy_labels() -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}/tenant": TENANT_ID,
        f"{LABEL_PREFIX}/api-id": API_ID,
        f"{LABEL_PREFIX}/managed-by": "gitops",
        f"{LABEL_PREFIX}/goal": GOAL_LABEL,
        f"{LABEL_PREFIX}/change-class": "standard",
        f"{LABEL_PREFIX}/response-policy": "security-headers",
    }


def response_policy_annotations() -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}/runbook": ROLLBACK_RUNBOOK,
        f"{LABEL_PREFIX}/docs": relative(DOC_PATH),
        f"{LABEL_PREFIX}/governance-policy": "goal-008-kong-governance-policy-as-code",
    }


def response_headers_plugin() -> dict[str, Any]:
    product = api_product()
    labels = response_policy_labels()
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
                **response_policy_annotations(),
            },
            "labels": labels,
        },
        "plugin": PLUGIN_TYPE,
        "config": {"add": {"headers": list(REQUIRED_HEADER_LINES)}},
    }


def stable_accounts_route() -> dict[str, Any]:
    product = api_product()
    for doc in ownership_resources():
        if doc.get("kind") == "HTTPRoute" and doc.get("metadata", {}).get("name") == ROUTE_NAME:
            return annotate(doc, product, TENANT_ID, "standard")
    raise ValueError(f"missing HTTPRoute/{NAMESPACE}/{ROUTE_NAME}")


def route_with_response_headers_plugin() -> dict[str, Any]:
    route = deepcopy(stable_accounts_route())
    metadata = route.setdefault("metadata", {})
    metadata.setdefault("labels", {}).update(response_policy_labels())
    metadata.setdefault("annotations", {}).update(response_policy_annotations())
    annotations = metadata["annotations"]
    plugins = [plugin.strip() for plugin in annotations.get("konghq.com/plugins", "").split(",") if plugin.strip()]
    if PLUGIN_NAME not in plugins:
        plugins.append(PLUGIN_NAME)
    annotations["konghq.com/plugins"] = ",".join(plugins)
    return route


def render(plugin_only: bool = False) -> list[dict[str, Any]]:
    plugin = response_headers_plugin()
    if plugin_only:
        return [plugin]
    return [plugin, route_with_response_headers_plugin()]


def rollback_resources() -> list[dict[str, Any]]:
    return [stable_accounts_route()]


def unsafe_request_transformer_fixture() -> list[dict[str, Any]]:
    fixture = response_headers_plugin()
    fixture["metadata"]["name"] = "banklab-goal009-unsafe-request-transformer"
    fixture["plugin"] = "request-transformer"
    fixture["config"] = {"add": {"headers": ["X-BankLab-Unsafe: denied"]}}
    return [fixture]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-only", action="store_true", help="render only the goal009 KongPlugin for deletion")
    parser.add_argument("--rollback", action="store_true", help="render stable route resources without the goal009 plugin")
    parser.add_argument("--unsafe-fixture", action="store_true", help="render an unsafe request-transformer fixture")
    args = parser.parse_args()
    if args.unsafe_fixture:
        docs = unsafe_request_transformer_fixture()
    else:
        docs = rollback_resources() if args.rollback else render(plugin_only=args.plugin_only)
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
