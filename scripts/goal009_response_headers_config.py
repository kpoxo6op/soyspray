"""Goal009 governed response headers model."""

from __future__ import annotations

from pathlib import Path

try:
    from scripts.synthetic_bank_config import ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import ROOT


GOAL_ID = "goal-009-kong-governed-response-headers"
GOAL_LABEL = "goal-009"
API_ID = "accounts"
TENANT_ID = "retail-accounts"
NAMESPACE = "tenant-accounts"
ROUTE_NAME = "banklab-accounts"
SERVICE_NAME = "banklab-accounts-api"
PLUGIN_NAME = "banklab-goal009-security-headers"
PLUGIN_TYPE = "response-transformer"
HOST = "api.internal.banklab.test"
HEALTH_PATH = "/accounts/v1/health"
EXPECTED_BODY_MARKER = "banklab-accounts-ok"
CONSUMER_CLIENT = "mobile-banking-app"
WRONG_ACL_CLIENT = "internet-banking-web"

REQUIRED_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("X-BankLab-Response-Policy", "goal009"),
)
REQUIRED_HEADER_LINES = tuple(f"{name}: {value}" for name, value in REQUIRED_HEADERS)

REQUIRED_BASE_PLUGINS = (
    "banklab-key-auth",
    "banklab-acl",
    "banklab-rate-limit",
    "banklab-correlation-id",
)

FORBIDDEN_PLUGIN_TYPES = {
    "request-transformer",
    "pre-function",
    "post-function",
    "file-log",
    "syslog",
    "openid-connect",
    "opa",
    "rate-limiting-advanced",
}

DOC_PATH = ROOT / "docs/platform/governed-response-headers.md"
ROLLBACK_RUNBOOK = "docs/runbooks/goal-009-governed-response-headers-rollback.md"


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))
