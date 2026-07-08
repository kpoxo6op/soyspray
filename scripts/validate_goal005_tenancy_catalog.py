#!/usr/bin/env python3
"""Validate goal005 tenant and API product catalog consistency."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts.goal005_tenancy_config import (
        APIS,
        CATALOG_REQUIRED_FIELDS,
        CHANGE_CONTROL_DIR,
        REQUIRED_CHANGE_CLASSES,
        ROOT,
        TENANT_REQUIRED_FIELDS,
        VALID_DATA_CLASSIFICATIONS,
        VALID_EXPOSURES,
        expected_authz_model,
        expected_required_plugins,
        load_api_products,
        load_tenants,
        load_yaml,
        sample_change,
    )
except ModuleNotFoundError:
    from goal005_tenancy_config import (
        APIS,
        CATALOG_REQUIRED_FIELDS,
        CHANGE_CONTROL_DIR,
        REQUIRED_CHANGE_CLASSES,
        ROOT,
        TENANT_REQUIRED_FIELDS,
        VALID_DATA_CLASSIFICATIONS,
        VALID_EXPOSURES,
        expected_authz_model,
        expected_required_plugins,
        load_api_products,
        load_tenants,
        load_yaml,
        sample_change,
    )


REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/goal-005-tenancy-rbac-change-control.md",
    "platform/catalog/tenants.yaml",
    "platform/change-control/change-classes.yaml",
    "platform/change-control/sample-changes/goal-005-normal-change.yaml",
    "docs/platform/tenancy-model.md",
    "docs/platform/change-control.md",
    "docs/platform/api-product-onboarding.md",
    "docs/runbooks/goal-005-rbac-failure.md",
    "docs/runbooks/goal-005-change-rollback.md",
    "docs/decisions/goal-005-tenancy-rbac-change-control.md",
]


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def raw_yaml(relative: str) -> dict:
    return load_yaml(ROOT / relative)


def validate_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        require((ROOT / relative).is_file(), errors, f"missing required goal005 file: {relative}")
    for api in APIS:
        require((ROOT / "platform/catalog/api-products" / f"{api.key}.yaml").is_file(), errors, f"missing API product file for {api.key}")


def validate_catalog(errors: list[str]) -> None:
    raw_tenants = raw_yaml("platform/catalog/tenants.yaml").get("tenants", [])
    for entry in raw_tenants:
        missing = TENANT_REQUIRED_FIELDS - set(entry)
        require(not missing, errors, f"tenant {entry.get('tenant_id', '<unknown>')} missing fields: {sorted(missing)}")

    tenants = load_tenants()
    products = load_api_products()
    tenant_ids = [tenant.tenant_id for tenant in tenants]
    require(len(tenant_ids) == len(set(tenant_ids)), errors, "tenant IDs must be unique")
    tenant_by_id = {tenant.tenant_id: tenant for tenant in tenants}
    api_ids = {api.key for api in APIS}
    product_ids = [product.api_id for product in products]
    require(set(product_ids) == api_ids, errors, f"API product catalog must contain exactly {sorted(api_ids)}")
    require(len(product_ids) == len(set(product_ids)), errors, "API products must be unique")

    owned: list[str] = []
    for tenant in tenants:
        require(tenant.owned_api_ids, errors, f"tenant {tenant.tenant_id} must own at least one API")
        for api_id in tenant.owned_api_ids:
            require(api_id in api_ids, errors, f"tenant {tenant.tenant_id} references unknown API {api_id}")
            owned.append(api_id)
    require(set(owned) == api_ids, errors, "each API must be owned by exactly one tenant")
    require(len(owned) == len(set(owned)), errors, "an API is owned by more than one tenant")

    products_by_id = {product.api_id: product for product in products}
    for product in products:
        raw = raw_yaml(f"platform/catalog/api-products/{product.api_id}.yaml")
        missing = CATALOG_REQUIRED_FIELDS - set(raw)
        require(not missing, errors, f"API product {product.api_id} missing fields: {sorted(missing)}")
        require(product.tenant_id in tenant_by_id, errors, f"API product {product.api_id} references unknown tenant {product.tenant_id}")
        tenant = tenant_by_id.get(product.tenant_id)
        if tenant is None:
            continue
        require(product.api_id in tenant.owned_api_ids, errors, f"API product {product.api_id} is not in tenant ownership list")
        require(product.namespace in tenant.api_namespaces, errors, f"API product {product.api_id} namespace is outside tenant API namespaces")
        require(product.exposure in VALID_EXPOSURES, errors, f"API product {product.api_id} has invalid exposure")
        require(product.exposure in tenant.allowed_exposure, errors, f"tenant {tenant.tenant_id} does not allow exposure {product.exposure}")
        require(product.data_classification in VALID_DATA_CLASSIFICATIONS, errors, f"API product {product.api_id} has invalid data classification")
        require(
            product.data_classification in tenant.data_classifications_allowed,
            errors,
            f"tenant {tenant.tenant_id} does not allow data classification {product.data_classification}",
        )
        require(product.required_plugins == expected_required_plugins(product.api_id), errors, f"API product {product.api_id} required plugins mismatch")
        for plugin in (*product.required_plugins, *product.optional_tenant_plugins):
            require(plugin in tenant.allowed_plugins, errors, f"tenant {tenant.tenant_id} does not allow plugin {plugin} for {product.api_id}")
        require(product.authz_model == expected_authz_model(product.api_id), errors, f"API product {product.api_id} authz model mismatch")
        require(product.credential_owner == "platform", errors, f"API product {product.api_id} credential_owner must be platform")
        require(bool(product.runbook), errors, f"API product {product.api_id} must declare a runbook")
        if product.data_classification in {"confidential", "restricted"}:
            require((ROOT / product.runbook).is_file(), errors, f"API product {product.api_id} runbook does not exist")


def validate_change_control(errors: list[str]) -> None:
    classes = raw_yaml("platform/change-control/change-classes.yaml").get("change_classes", {})
    require(set(classes) == REQUIRED_CHANGE_CLASSES, errors, f"change classes must be {sorted(REQUIRED_CHANGE_CLASSES)}")
    for name, entry in classes.items():
        for field in (
            "required_approver_type",
            "minimum_evidence",
            "rollback_required",
            "runtime_smoke_mandatory",
            "security_review_mandatory",
            "tenant_self_service_allowed",
        ):
            require(field in entry, errors, f"change class {name} missing {field}")
    require(classes.get("normal", {}).get("rollback_required") is True, errors, "normal changes must require rollback")
    require(classes.get("security", {}).get("security_review_mandatory") is True, errors, "security changes must require security review")
    require(
        "retrospective review" in classes.get("emergency", {}).get("minimum_evidence", []),
        errors,
        "emergency changes must require retrospective evidence",
    )
    change = sample_change()
    tenants = {tenant.tenant_id for tenant in load_tenants()}
    products = {product.api_id for product in load_api_products()}
    require(change.get("tenant_id") in tenants, errors, "sample change references an unknown tenant")
    require(change.get("api_id") in products, errors, "sample change references an unknown API")
    require(change.get("change_class") == "normal", errors, "sample change must be normal class")
    require("rollback_command" in change, errors, "sample change must have rollback command")
    require(bool(change.get("expected_runtime_evidence")), errors, "sample change evidence contract is incomplete")


def validate() -> list[str]:
    errors: list[str] = []
    validate_required_files(errors)
    validate_catalog(errors)
    validate_change_control(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Goal005 tenancy catalog validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Goal005 tenancy catalog validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
