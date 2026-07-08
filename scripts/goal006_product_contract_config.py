"""Goal006 self-service API product contract model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.goal005_tenancy_config import load_api_products, load_tenants, load_yaml
    from scripts.synthetic_bank_config import ROOT
except ModuleNotFoundError:
    from goal005_tenancy_config import load_api_products, load_tenants, load_yaml
    from synthetic_bank_config import ROOT


GOAL_ID = "goal-006-self-service-api-product-contract"
GOAL_LABEL = "goal-006"
PRODUCT_ID = "accounts-self-service-health-v1"
API_ID = "accounts"
TENANT_ID = "retail-accounts"
NAMESPACE = "tenant-accounts"
ROUTE_NAME = "banklab-accounts"
SERVICE_NAME = "banklab-accounts-api"
PLUGIN_NAME = "goal006-product-contract-header"
PLUGIN_TYPE = "response-transformer"
HEADER_NAME = "X-Banklab-Product-Contract"
HEADER_VALUE = PRODUCT_ID
HOST = "api.internal.banklab.test"
HEALTH_PATH = "/accounts/v1/health"
EXPECTED_BODY_MARKER = "banklab-accounts-ok"
CONSUMER_CLIENT = "mobile-banking-app"
WRONG_ACL_CLIENT = "internet-banking-web"

CONTRACT_PATH = ROOT / "platform/self-service/api-products/accounts-self-service-health-v1.yaml"
DECK_STATE_PATH = ROOT / "platform/kong/deck/goal006/accounts-self-service-product.yaml"
ROLLBACK_RUNBOOK = "docs/runbooks/goal-006-product-contract-rollback.md"

REQUIRED_BASE_PLUGINS = (
    "banklab-key-auth",
    "banklab-acl",
    "banklab-rate-limit",
    "banklab-correlation-id",
)


def load_product_contract() -> dict[str, Any]:
    return load_yaml(CONTRACT_PATH)


def load_deck_state() -> dict[str, Any]:
    return yaml.safe_load(DECK_STATE_PATH.read_text(encoding="utf-8")) or {}


def api_product() -> Any:
    for product in load_api_products():
        if product.api_id == API_ID:
            return product
    raise KeyError(API_ID)


def tenant() -> Any:
    for entry in load_tenants():
        if entry.tenant_id == TENANT_ID:
            return entry
    raise KeyError(TENANT_ID)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))
