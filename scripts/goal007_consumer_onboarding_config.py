"""Goal007 self-service consumer onboarding model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from scripts.goal006_product_contract_config import PRODUCT_ID as TARGET_PRODUCT_ID
    from scripts.goal005_tenancy_config import load_yaml
    from scripts.synthetic_bank_config import ROOT, api_access_group
except ModuleNotFoundError:
    from goal006_product_contract_config import PRODUCT_ID as TARGET_PRODUCT_ID
    from goal005_tenancy_config import load_yaml
    from synthetic_bank_config import ROOT, api_access_group


GOAL_ID = "goal-007-consumer-onboarding-entitlements"
GOAL_LABEL = "goal-007"
CONSUMER_ID = "branch-insights-app"
CONSUMER_TEAM = "branch-insights"
NAMESPACE = "synthetic-clients"
TARGET_API_ID = "accounts"
TARGET_TENANT_ID = "retail-accounts"
ACL_GROUP = api_access_group(TARGET_API_ID)
KEY_AUTH_SECRET_NAME = "banklab-branch-insights-app-key-auth"
ACL_SECRET_NAME = "banklab-branch-insights-app-accounts-acl"
CONSUMER_API_KEY_ENV = "BANKLAB_BRANCH_INSIGHTS_APP_API_KEY"
WRONG_ACL_CLIENT_SECRET = "banklab-internet-banking-web-key-auth"
HOST = "api.internal.banklab.test"
HEALTH_PATH = "/accounts/v1/health"
EXPECTED_BODY_MARKER = "banklab-accounts-ok"
CONSUMER_CONTRACT_PATH = ROOT / "platform/self-service/consumer-contracts/branch-insights-app-accounts.yaml"
ROLLBACK_RUNBOOK = "docs/runbooks/goal-007-consumer-onboarding-rollback.md"
MIN_SECRET_LENGTH = 20


def load_consumer_contract() -> dict[str, Any]:
    return load_yaml(CONSUMER_CONTRACT_PATH)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))
