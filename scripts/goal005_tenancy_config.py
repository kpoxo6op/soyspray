"""Goal005 tenancy, catalog, RBAC, and sample-change model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.synthetic_bank_config import APIS, ROOT, api_access_group, api_auth_plugin
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, ROOT, api_access_group, api_auth_plugin


CATALOG_DIR = ROOT / "platform/catalog"
API_PRODUCT_DIR = CATALOG_DIR / "api-products"
CHANGE_CONTROL_DIR = ROOT / "platform/change-control"
SAMPLE_CHANGE_PATH = CHANGE_CONTROL_DIR / "sample-changes/goal-005-normal-change.yaml"

TENANT_SERVICE_ACCOUNTS = {
    "retail-accounts": "retail-accounts-api-applier",
    "payments": "payments-api-applier",
    "risk-compliance": "risk-compliance-api-applier",
}

PLATFORM_SERVICE_ACCOUNT = "kong-platform-change-applier"
PLATFORM_NAMESPACE = "platform-kong"
CATALOG_CONFIGMAP = "goal005-tenant-catalog"
TENANT_ROLE_NAME = "goal005-tenant-api-applier"
TENANT_ROLE_BINDING_NAME = "goal005-tenant-api-applier"
PLATFORM_ROLE_NAME = "goal005-platform-change-reader"
PLATFORM_ROLE_BINDING_NAME = "goal005-platform-change-reader"

GOAL005_LABEL_PREFIX = "platform.soyspray.io"
SAMPLE_CHANGE_ID = "goal-005-normal-change"
SAMPLE_CHANGE_API_ID = "accounts"
SAMPLE_CHANGE_PLUGIN_NAME = "goal005-normal-change-header"
SAMPLE_CHANGE_HEADER = "X-Goal005-Change-Id"
SAMPLE_CHANGE_HEADER_VALUE = "goal-005-normal-change"
SAMPLE_CHANGE_PLUGIN_TYPE = "response-transformer"

VALID_EXPOSURES = {"internal", "external"}
VALID_DATA_CLASSIFICATIONS = {"internal", "confidential", "restricted"}
REQUIRED_CHANGE_CLASSES = {"standard", "normal", "emergency", "security"}
CATALOG_REQUIRED_FIELDS = {
    "api_id",
    "display_name",
    "tenant_id",
    "namespace",
    "logical_workspace",
    "exposure",
    "data_classification",
    "authn_model",
    "authz_model",
    "kong_service_name",
    "kong_route_names",
    "required_plugins",
    "optional_tenant_plugins",
    "credential_owner",
    "slo",
    "runbook",
    "docs_owner",
    "lifecycle_state",
}
TENANT_REQUIRED_FIELDS = {
    "tenant_id",
    "display_name",
    "logical_workspace",
    "namespace",
    "owned_api_ids",
    "allowed_exposure",
    "allowed_plugins",
    "data_classifications_allowed",
    "support_contact",
    "reviewers",
    "break_glass_contact",
    "change_approval_group",
}


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    display_name: str
    logical_workspace: str
    namespace: str
    api_namespaces: tuple[str, ...]
    owned_api_ids: tuple[str, ...]
    allowed_exposure: tuple[str, ...]
    allowed_plugins: tuple[str, ...]
    data_classifications_allowed: tuple[str, ...]
    support_contact: str
    reviewers: tuple[str, ...]
    break_glass_contact: str
    change_approval_group: str


@dataclass(frozen=True)
class ApiProduct:
    api_id: str
    display_name: str
    tenant_id: str
    namespace: str
    logical_workspace: str
    exposure: str
    data_classification: str
    authn_model: str
    authz_model: str
    kong_service_name: str
    kong_route_names: tuple[str, ...]
    required_plugins: tuple[str, ...]
    optional_tenant_plugins: tuple[str, ...]
    credential_owner: str
    slo: dict[str, Any]
    runbook: str
    docs_owner: str
    lifecycle_state: str


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_tenants() -> list[Tenant]:
    data = load_yaml(CATALOG_DIR / "tenants.yaml")
    tenants: list[Tenant] = []
    for entry in data.get("tenants", []):
        tenants.append(
            Tenant(
                tenant_id=entry["tenant_id"],
                display_name=entry["display_name"],
                logical_workspace=entry["logical_workspace"],
                namespace=entry["namespace"],
                api_namespaces=tuple(entry.get("api_namespaces", [entry["namespace"]])),
                owned_api_ids=tuple(entry["owned_api_ids"]),
                allowed_exposure=tuple(entry["allowed_exposure"]),
                allowed_plugins=tuple(entry["allowed_plugins"]),
                data_classifications_allowed=tuple(entry["data_classifications_allowed"]),
                support_contact=entry["support_contact"],
                reviewers=tuple(entry["reviewers"]),
                break_glass_contact=entry["break_glass_contact"],
                change_approval_group=entry["change_approval_group"],
            )
        )
    return tenants


def load_api_products() -> list[ApiProduct]:
    products: list[ApiProduct] = []
    for path in sorted(API_PRODUCT_DIR.glob("*.yaml")):
        entry = load_yaml(path)
        products.append(
            ApiProduct(
                api_id=entry["api_id"],
                display_name=entry["display_name"],
                tenant_id=entry["tenant_id"],
                namespace=entry["namespace"],
                logical_workspace=entry["logical_workspace"],
                exposure=entry["exposure"],
                data_classification=entry["data_classification"],
                authn_model=entry["authn_model"],
                authz_model=entry["authz_model"],
                kong_service_name=entry["kong_service_name"],
                kong_route_names=tuple(entry["kong_route_names"]),
                required_plugins=tuple(entry["required_plugins"]),
                optional_tenant_plugins=tuple(entry["optional_tenant_plugins"]),
                credential_owner=entry["credential_owner"],
                slo=entry["slo"],
                runbook=entry["runbook"],
                docs_owner=entry["docs_owner"],
                lifecycle_state=entry["lifecycle_state"],
            )
        )
    return products


def tenants_by_id() -> dict[str, Tenant]:
    return {tenant.tenant_id: tenant for tenant in load_tenants()}


def products_by_id() -> dict[str, ApiProduct]:
    return {product.api_id: product for product in load_api_products()}


def api_by_id() -> dict[str, Any]:
    return {api.key: api for api in APIS}


def expected_required_plugins(api_id: str) -> tuple[str, ...]:
    plugins = ["jwt" if api_auth_plugin(api_id) == "jwt" else "key-auth", "acl", "rate-limiting", "correlation-id"]
    return tuple(plugins)


def expected_authz_model(api_id: str) -> str:
    return f"acl:{api_access_group(api_id)}"


def sample_change() -> dict[str, Any]:
    return load_yaml(SAMPLE_CHANGE_PATH)
