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
