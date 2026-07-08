from scripts.goal005_tenancy_config import (
    APIS,
    VALID_DATA_CLASSIFICATIONS,
    VALID_EXPOSURES,
    load_api_products,
    load_tenants,
)
from scripts.validate_goal005_tenancy_catalog import validate


def test_all_six_apis_are_present():
    assert {product.api_id for product in load_api_products()} == {api.key for api in APIS}


def test_tenant_ids_are_unique():
    tenant_ids = [tenant.tenant_id for tenant in load_tenants()]
    assert len(tenant_ids) == len(set(tenant_ids))


def test_each_api_has_exactly_one_tenant():
    owned = [api_id for tenant in load_tenants() for api_id in tenant.owned_api_ids]
    assert sorted(owned) == sorted(api.key for api in APIS)
    assert len(owned) == len(set(owned))


def test_each_tenant_owns_at_least_one_api():
    assert all(tenant.owned_api_ids for tenant in load_tenants())


def test_required_fields_and_value_sets_are_valid():
    for product in load_api_products():
        assert product.exposure in VALID_EXPOSURES
        assert product.data_classification in VALID_DATA_CLASSIFICATIONS
        assert product.credential_owner == "platform"
        assert product.runbook


def test_plugin_allowlists_are_enforced():
    tenants = {tenant.tenant_id: tenant for tenant in load_tenants()}
    for product in load_api_products():
        tenant = tenants[product.tenant_id]
        for plugin in (*product.required_plugins, *product.optional_tenant_plugins):
            assert plugin in tenant.allowed_plugins


def test_catalog_validator_passes():
    assert validate() == []
