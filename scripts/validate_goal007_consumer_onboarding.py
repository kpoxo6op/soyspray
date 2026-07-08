#!/usr/bin/env python3
"""Validate goal007 consumer onboarding contracts and rendered resources."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from scripts.goal004_security_config import CLIENTS, CLIENT_FOR_API, acl_secret_name, key_auth_secret_name
    from scripts.goal007_consumer_onboarding_config import (
        ACL_GROUP,
        ACL_SECRET_NAME,
        CONSUMER_API_KEY_ENV,
        CONSUMER_ID,
        CONSUMER_TEAM,
        KEY_AUTH_SECRET_NAME,
        NAMESPACE,
        TARGET_API_ID,
        TARGET_PRODUCT_ID,
        TARGET_TENANT_ID,
        load_consumer_contract,
    )
    from scripts.goal006_product_contract_config import load_product_contract
    from scripts.render_goal007_consumer_onboarding import delete_resources, render
    from scripts.render_goal007_runtime_credentials import render as render_credentials
    from scripts.synthetic_bank_config import api_access_group
except ModuleNotFoundError:
    from goal004_security_config import CLIENTS, CLIENT_FOR_API, acl_secret_name, key_auth_secret_name
    from goal007_consumer_onboarding_config import (
        ACL_GROUP,
        ACL_SECRET_NAME,
        CONSUMER_API_KEY_ENV,
        CONSUMER_ID,
        CONSUMER_TEAM,
        KEY_AUTH_SECRET_NAME,
        NAMESPACE,
        TARGET_API_ID,
        TARGET_PRODUCT_ID,
        TARGET_TENANT_ID,
        load_consumer_contract,
    )
    from goal006_product_contract_config import load_product_contract
    from render_goal007_consumer_onboarding import delete_resources, render
    from render_goal007_runtime_credentials import render as render_credentials
    from synthetic_bank_config import api_access_group


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def docs_by_kind(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc.get("kind") == kind]


@contextmanager
def temporary_env(name: str, value: str) -> Iterator[None]:
    old = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


def validate() -> list[str]:
    errors: list[str] = []
    contract = load_consumer_contract()
    product = load_product_contract()

    require(contract.get("consumer_id") == CONSUMER_ID, errors, "consumer_id mismatch")
    require(contract.get("owning_team") == CONSUMER_TEAM, errors, "owning_team mismatch")
    require(contract.get("target_product_id") == TARGET_PRODUCT_ID, errors, "target_product_id mismatch")
    require(product.get("product_id") == TARGET_PRODUCT_ID, errors, "target product contract missing")
    require(contract.get("target_api_id") == TARGET_API_ID == product.get("api_id"), errors, "target API mismatch")
    require(contract.get("target_tenant_id") == TARGET_TENANT_ID == product.get("tenant_id"), errors, "target tenant mismatch")
    require(contract.get("namespace") == NAMESPACE, errors, "consumer namespace mismatch")
    require(contract.get("allowed_acl_group") == ACL_GROUP == api_access_group(TARGET_API_ID), errors, "ACL group mismatch")
    require(contract.get("credential_owner") == "platform", errors, "credential owner must remain platform")
    require(contract.get("credential_source") == "runtime-generated-not-committed", errors, "credential source mismatch")
    refs = contract.get("credential_references", {})
    require(refs.get("key_auth_secret") == KEY_AUTH_SECRET_NAME, errors, "key-auth secret reference mismatch")
    require(refs.get("acl_secret") == ACL_SECRET_NAME, errors, "ACL secret reference mismatch")
    require(refs.get("key_env_var") == CONSUMER_API_KEY_ENV, errors, "key env var reference mismatch")
    require(CONSUMER_ID not in set(CLIENTS), errors, "consumer_id must not duplicate existing goal004 clients")
    require(KEY_AUTH_SECRET_NAME != ACL_SECRET_NAME, errors, "credential references must be unique")
    existing_key_secrets = {key_auth_secret_name(client) for client in CLIENTS if client != "external-fintech-partner"}
    existing_acl_secrets = {
        acl_secret_name(client, api_key)
        for api_key, client in CLIENT_FOR_API.items()
        if client != "external-fintech-partner"
    }
    require(KEY_AUTH_SECRET_NAME not in existing_key_secrets, errors, "key-auth secret must not duplicate an existing consumer key")
    require(ACL_SECRET_NAME not in existing_acl_secrets, errors, "ACL secret must not duplicate an existing consumer ACL binding")
    require(contract.get("review_date") < contract.get("expires_on"), errors, "review_date must be before expires_on")

    rendered = render()
    require(len(docs_by_kind(rendered, "KongConsumer")) == 1, errors, "render must produce one KongConsumer")
    require(not docs_by_kind(rendered, "Secret"), errors, "static goal007 renderer must not emit Secrets")
    consumer = docs_by_kind(rendered, "KongConsumer")[0]
    require(consumer["metadata"]["namespace"] == NAMESPACE, errors, "rendered consumer namespace mismatch")
    require(consumer["username"] == CONSUMER_ID, errors, "rendered consumer username mismatch")
    require(consumer["credentials"] == [KEY_AUTH_SECRET_NAME, ACL_SECRET_NAME], errors, "rendered consumer credentials mismatch")

    delete_docs = delete_resources()
    require(len(docs_by_kind(delete_docs, "Secret")) == 2, errors, "delete render must include two Secret references")

    with temporary_env(CONSUMER_API_KEY_ENV, "goal007-branch-insights-key-0001"):
        credentials = render_credentials()
    secrets = {secret["metadata"]["name"]: secret for secret in docs_by_kind(credentials, "Secret")}
    require(set(secrets) == {KEY_AUTH_SECRET_NAME, ACL_SECRET_NAME}, errors, "runtime credentials set mismatch")
    require(secrets[KEY_AUTH_SECRET_NAME]["stringData"].keys() == {"key"}, errors, "key-auth Secret must only contain key")
    require(secrets[ACL_SECRET_NAME]["stringData"] == {"group": ACL_GROUP}, errors, "ACL Secret group mismatch")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"goal007 validation failed: {error}", file=sys.stderr)
        return 1
    print("goal007 consumer onboarding validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
