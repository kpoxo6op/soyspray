"""Shared goal-003 synthetic API metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SyntheticApi:
    key: str
    title: str
    namespace: str
    owner: str
    exposure: str
    host: str
    prefix: str
    gateway: str
    marker: str
    client: str


APIS = (
    SyntheticApi("accounts", "Accounts", "tenant-accounts", "tenant-accounts-team", "internal", "api.internal.banklab.test", "/accounts/v1", "kong-internal", "banklab-accounts-ok", "mobile-banking-app"),
    SyntheticApi("payments", "Payments", "tenant-payments", "tenant-payments-team", "internal", "api.internal.banklab.test", "/payments/v1", "kong-internal", "banklab-payments-ok", "payments-processor"),
    SyntheticApi("cards", "Cards", "tenant-cards", "tenant-cards-team", "internal", "api.internal.banklab.test", "/cards/v1", "kong-internal", "banklab-cards-ok", "internet-banking-web"),
    SyntheticApi("customer-profile", "Customer Profile", "tenant-customer-profile", "tenant-customer-profile-team", "internal", "api.internal.banklab.test", "/customers/v1", "kong-internal", "banklab-customer-profile-ok", "internal-crm"),
    SyntheticApi("fraud-decisions", "Fraud Decisions", "tenant-fraud", "tenant-fraud-team", "internal", "api.internal.banklab.test", "/fraud/v1", "kong-internal", "banklab-fraud-decisions-ok", "fraud-platform"),
    SyntheticApi("open-banking", "Open Banking Partner", "tenant-open-banking", "tenant-open-banking-team", "external", "api.external.banklab.test", "/open-banking/v1", "kong-external", "banklab-open-banking-ok", "external-fintech-partner"),
)


CLIENTS = (
    "mobile-banking-app",
    "internet-banking-web",
    "internal-crm",
    "fraud-platform",
    "payments-processor",
    "external-fintech-partner",
)

AUTH_PROFILE = "kong-oss-goal004-auth"
AUTH_STATE = "authenticated-required"
AUTHORIZATION_PROFILE = "acl-goal004-api-groups"
INTERNAL_RATE_LIMIT_PROFILE = "goal004-internal-redis-3rps"
EXTERNAL_RATE_LIMIT_PROFILE = "goal004-external-redis-3rps"
INTERNAL_RATE_LIMIT_PER_SECOND = 3
EXTERNAL_RATE_LIMIT_PER_SECOND = 3
RUNTIME_CREDENTIAL_SOURCE = "runtime-generated-not-committed"
REDIS_SERVICE_HOST = "banklab-rate-limit-redis.platform-kong.svc.cluster.local"
REDIS_SERVICE_PORT = 6379
CORRELATION_ID_HEADER = "X-Banklab-Correlation-ID"

CLIENT_API_ACCESS = {
    "mobile-banking-app": ("accounts",),
    "internet-banking-web": ("cards",),
    "internal-crm": ("customer-profile",),
    "fraud-platform": ("fraud-decisions",),
    "payments-processor": ("payments",),
    "external-fintech-partner": ("open-banking",),
}


BASE_LABELS = {
    "banklab.konghq.com/managed-by": "gitops",
    "banklab.konghq.com/platform-layer": "synthetic-api",
    "banklab.konghq.com/environment": "lab",
    "banklab.konghq.com/data-classification": "synthetic",
    "banklab.konghq.com/lifecycle": "sandbox",
    "banklab.konghq.com/auth-profile": "none-temporary-goal003-sandbox",
    "banklab.konghq.com/auth-state": "temporary-no-auth",
    "banklab.konghq.com/goal": "goal-003",
}


FORBIDDEN_KINDS = {
    "KongPlugin",
    "KongClusterPlugin",
    "KongConsumer",
    "KongConsumerGroup",
    "KongIngress",
    "TCPIngress",
    "UDPIngress",
    "Secret",
}


def api_access_group(api_key: str) -> str:
    return f"banklab-{api_key}"


def api_rate_limit_profile(exposure: str) -> str:
    return EXTERNAL_RATE_LIMIT_PROFILE if exposure == "external" else INTERNAL_RATE_LIMIT_PROFILE


def api_rate_limit_per_second(exposure: str) -> int:
    return EXTERNAL_RATE_LIMIT_PER_SECOND if exposure == "external" else INTERNAL_RATE_LIMIT_PER_SECOND


def api_auth_plugin(api_key: str) -> str:
    return "jwt" if api_key == "open-banking" else "key-auth"


def api_plugin_annotation(api_key: str) -> str:
    auth_plugin = "banklab-jwt" if api_auth_plugin(api_key) == "jwt" else "banklab-key-auth"
    return f"{auth_plugin},banklab-acl,banklab-rate-limit,banklab-correlation-id"


def client_env_var(client_name: str) -> str:
    normalized = client_name.upper().replace("-", "_")
    return f"BANKLAB_{normalized}_API_KEY"


def jwt_key_env_var() -> str:
    return "BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_KEY"


def jwt_secret_env_var() -> str:
    return "BANKLAB_EXTERNAL_FINTECH_PARTNER_JWT_SECRET"
