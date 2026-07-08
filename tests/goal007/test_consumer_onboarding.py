import os

import pytest

from scripts.goal004_security_config import CLIENTS, CLIENT_FOR_API, acl_secret_name, key_auth_secret_name
from scripts.goal007_consumer_onboarding_config import (
    ACL_GROUP,
    ACL_SECRET_NAME,
    CONSUMER_API_KEY_ENV,
    CONSUMER_ID,
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
from scripts.validate_goal007_consumer_onboarding import validate
from scripts.synthetic_bank_config import api_access_group


def docs(kind, rendered=None):
    rendered = render() if rendered is None else rendered
    return [doc for doc in rendered if doc.get("kind") == kind]


def test_consumer_contract_targets_goal006_product():
    contract = load_consumer_contract()
    product = load_product_contract()
    assert contract["consumer_id"] == CONSUMER_ID
    assert contract["target_product_id"] == TARGET_PRODUCT_ID == product["product_id"]
    assert contract["target_api_id"] == TARGET_API_ID == product["api_id"]
    assert contract["target_tenant_id"] == TARGET_TENANT_ID == product["tenant_id"]
    assert contract["allowed_acl_group"] == ACL_GROUP == api_access_group(TARGET_API_ID)


def test_consumer_contract_uses_new_consumer_name():
    assert CONSUMER_ID not in set(CLIENTS)


def test_consumer_contract_uses_new_credential_references():
    existing_key_secrets = {key_auth_secret_name(client) for client in CLIENTS if client != "external-fintech-partner"}
    existing_acl_secrets = {
        acl_secret_name(client, api_key)
        for api_key, client in CLIENT_FOR_API.items()
        if client != "external-fintech-partner"
    }
    assert KEY_AUTH_SECRET_NAME not in existing_key_secrets
    assert ACL_SECRET_NAME not in existing_acl_secrets
    assert KEY_AUTH_SECRET_NAME != ACL_SECRET_NAME


def test_static_render_emits_consumer_without_secrets():
    rendered = render()
    assert len(docs("KongConsumer", rendered)) == 1
    assert not docs("Secret", rendered)
    consumer = docs("KongConsumer", rendered)[0]
    assert consumer["metadata"]["namespace"] == NAMESPACE
    assert consumer["username"] == CONSUMER_ID
    assert consumer["credentials"] == [KEY_AUTH_SECRET_NAME, ACL_SECRET_NAME]


def test_delete_render_references_consumer_and_credentials():
    rendered = delete_resources()
    assert docs("KongConsumer", rendered)[0]["metadata"]["name"] == CONSUMER_ID
    assert {secret["metadata"]["name"] for secret in docs("Secret", rendered)} == {KEY_AUTH_SECRET_NAME, ACL_SECRET_NAME}


def test_runtime_credentials_require_env(monkeypatch):
    monkeypatch.delenv(CONSUMER_API_KEY_ENV, raising=False)
    with pytest.raises(ValueError):
        render_credentials()


def test_runtime_credentials_render_key_and_acl_secrets(monkeypatch):
    monkeypatch.setenv(CONSUMER_API_KEY_ENV, "goal007-branch-insights-key-0001")
    secrets = {secret["metadata"]["name"]: secret for secret in docs("Secret", render_credentials())}
    assert secrets[KEY_AUTH_SECRET_NAME]["stringData"] == {"key": os.environ[CONSUMER_API_KEY_ENV]}
    assert secrets[ACL_SECRET_NAME]["stringData"] == {"group": ACL_GROUP}
    assert secrets[KEY_AUTH_SECRET_NAME]["metadata"]["labels"]["konghq.com/credential"] == "key-auth"
    assert secrets[ACL_SECRET_NAME]["metadata"]["labels"]["konghq.com/credential"] == "acl"


def test_goal007_validator_passes():
    assert validate() == []
