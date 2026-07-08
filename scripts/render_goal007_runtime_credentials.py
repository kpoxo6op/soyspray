#!/usr/bin/env python3
"""Render runtime-only goal007 credential Secrets from environment variables."""

from __future__ import annotations

import os
import sys
from typing import Any

import yaml

try:
    from scripts.goal007_consumer_onboarding_config import (
        ACL_GROUP,
        ACL_SECRET_NAME,
        CONSUMER_API_KEY_ENV,
        CONSUMER_ID,
        CONSUMER_TEAM,
        GOAL_LABEL,
        KEY_AUTH_SECRET_NAME,
        MIN_SECRET_LENGTH,
        NAMESPACE,
        TARGET_API_ID,
        TARGET_PRODUCT_ID,
        TARGET_TENANT_ID,
    )
except ModuleNotFoundError:
    from goal007_consumer_onboarding_config import (
        ACL_GROUP,
        ACL_SECRET_NAME,
        CONSUMER_API_KEY_ENV,
        CONSUMER_ID,
        CONSUMER_TEAM,
        GOAL_LABEL,
        KEY_AUTH_SECRET_NAME,
        MIN_SECRET_LENGTH,
        NAMESPACE,
        TARGET_API_ID,
        TARGET_PRODUCT_ID,
        TARGET_TENANT_ID,
    )


PLACEHOLDER_MARKERS = ("change", "placeholder", "example", "dummy", "password", "changeme", "replace")


def labels(credential_type: str) -> dict[str, str]:
    return {
        "banklab.konghq.com/managed-by": "runtime-guarded",
        "banklab.konghq.com/platform-layer": "consumer-onboarding",
        "banklab.konghq.com/environment": "lab",
        "banklab.konghq.com/data-classification": "synthetic",
        "banklab.konghq.com/lifecycle": "sandbox",
        "banklab.konghq.com/goal": GOAL_LABEL,
        "banklab.konghq.com/credential-source": "runtime-generated-not-committed",
        "banklab.konghq.com/client": CONSUMER_ID,
        "banklab.konghq.com/api-domain": TARGET_API_ID,
        "platform.soyspray.io/tenant": TARGET_TENANT_ID,
        "platform.soyspray.io/product-id": TARGET_PRODUCT_ID,
        "platform.soyspray.io/consumer-id": CONSUMER_ID,
        "platform.soyspray.io/consumer-team": CONSUMER_TEAM,
        "konghq.com/credential": credential_type,
    }


def secret(name: str, string_data: dict[str, str], secret_labels: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": NAMESPACE, "labels": secret_labels},
        "type": "Opaque",
        "stringData": string_data,
    }


def env_value() -> str:
    value = os.environ.get(CONSUMER_API_KEY_ENV, "")
    errors: list[str] = []
    if not value:
        errors.append(f"{CONSUMER_API_KEY_ENV} is missing")
    normalized = value.strip().lower()
    if len(value) < MIN_SECRET_LENGTH:
        errors.append(f"{CONSUMER_API_KEY_ENV} is too short")
    if any(marker in normalized for marker in PLACEHOLDER_MARKERS):
        errors.append(f"{CONSUMER_API_KEY_ENV} looks like a placeholder")
    if errors:
        raise ValueError("; ".join(errors))
    return value


def render() -> list[dict[str, Any]]:
    key = env_value()
    return [
        secret(KEY_AUTH_SECRET_NAME, {"key": key}, labels("key-auth")),
        secret(ACL_SECRET_NAME, {"group": ACL_GROUP}, labels("acl")),
    ]


def main() -> int:
    try:
        docs = render()
    except ValueError as exc:
        print(f"Goal007 runtime credential render failed: {exc}", file=sys.stderr)
        return 1
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
