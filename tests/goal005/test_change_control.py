from scripts.goal005_tenancy_config import ROOT, REQUIRED_CHANGE_CLASSES, load_api_products, load_tenants, load_yaml, sample_change


def change_classes():
    return load_yaml(ROOT / "platform/change-control/change-classes.yaml").get("change_classes", {})


def test_all_required_change_classes_exist():
    assert set(change_classes()) == REQUIRED_CHANGE_CLASSES


def test_normal_changes_require_rollback():
    assert change_classes()["normal"]["rollback_required"] is True


def test_security_changes_require_security_review():
    assert change_classes()["security"]["security_review_mandatory"] is True


def test_emergency_changes_require_retrospective_evidence():
    assert "retrospective review" in change_classes()["emergency"]["minimum_evidence"]


def test_sample_change_references_known_tenant_and_api():
    change = sample_change()
    assert change["tenant_id"] in {tenant.tenant_id for tenant in load_tenants()}
    assert change["api_id"] in {product.api_id for product in load_api_products()}


def test_sample_change_contract_is_complete():
    change = sample_change()
    assert change["rollback_command"] == "make goal005-change-rollback-and-smoke"
    assert change["expected_runtime_evidence"]
    assert change["affected_resources"]
