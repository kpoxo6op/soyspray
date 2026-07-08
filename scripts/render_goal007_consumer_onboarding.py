#!/usr/bin/env python3
"""Render goal007 consumer onboarding resources."""

from __future__ import annotations

import argparse
import sys
from typing import Any

import yaml

try:
    from scripts.goal007_consumer_onboarding_config import (
        ACL_SECRET_NAME,
        CONSUMER_CONTRACT_PATH,
        CONSUMER_ID,
        CONSUMER_TEAM,
        GOAL_LABEL,
        KEY_AUTH_SECRET_NAME,
        NAMESPACE,
        ROLLBACK_RUNBOOK,
        TARGET_API_ID,
        TARGET_PRODUCT_ID,
        TARGET_TENANT_ID,
        relative,
    )
except ModuleNotFoundError:
    from goal007_consumer_onboarding_config import (
        ACL_SECRET_NAME,
        CONSUMER_CONTRACT_PATH,
        CONSUMER_ID,
        CONSUMER_TEAM,
        GOAL_LABEL,
        KEY_AUTH_SECRET_NAME,
        NAMESPACE,
        ROLLBACK_RUNBOOK,
        TARGET_API_ID,
        TARGET_PRODUCT_ID,
        TARGET_TENANT_ID,
        relative,
    )


LABEL_PREFIX = "platform.soyspray.io"


def labels() -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}/managed-by": "gitops",
        f"{LABEL_PREFIX}/goal": GOAL_LABEL,
        f"{LABEL_PREFIX}/tenant": TARGET_TENANT_ID,
        f"{LABEL_PREFIX}/api-id": TARGET_API_ID,
        f"{LABEL_PREFIX}/product-id": TARGET_PRODUCT_ID,
        f"{LABEL_PREFIX}/consumer-id": CONSUMER_ID,
        f"{LABEL_PREFIX}/consumer-team": CONSUMER_TEAM,
    }


def annotations() -> dict[str, str]:
    return {
        "kubernetes.io/ingress.class": "kong",
        f"{LABEL_PREFIX}/runbook": ROLLBACK_RUNBOOK,
        f"{LABEL_PREFIX}/consumer-contract-file": relative(CONSUMER_CONTRACT_PATH),
    }


def consumer() -> dict[str, Any]:
    return {
        "apiVersion": "configuration.konghq.com/v1",
        "kind": "KongConsumer",
        "metadata": {
            "name": CONSUMER_ID,
            "namespace": NAMESPACE,
            "annotations": annotations(),
            "labels": labels(),
        },
        "username": CONSUMER_ID,
        "credentials": [KEY_AUTH_SECRET_NAME, ACL_SECRET_NAME],
    }


def delete_secret(name: str) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": NAMESPACE, "labels": labels()},
        "type": "Opaque",
    }


def render() -> list[dict[str, Any]]:
    return [consumer()]


def delete_resources() -> list[dict[str, Any]]:
    return [consumer(), delete_secret(KEY_AUTH_SECRET_NAME), delete_secret(ACL_SECRET_NAME)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="render metadata-only resources for deletion")
    args = parser.parse_args()
    docs = delete_resources() if args.delete else render()
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
