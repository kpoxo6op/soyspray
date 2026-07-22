from __future__ import annotations

from conftest import load_all

TENANTS = {
    "tenant-accounts",
    "tenant-payments",
    "tenant-cards",
    "tenant-customer-profile",
    "tenant-fraud",
    "tenant-open-banking",
}


def test_security_bundle_has_no_secret_values() -> None:
    resources = load_all("kubernetes/banklab/security/security-controls.yaml")
    assert not [resource for resource in resources if resource["kind"] == "Secret"]


def test_each_tenant_has_four_request_plugins() -> None:
    resources = load_all("kubernetes/banklab/security/security-controls.yaml")
    plugins = [resource for resource in resources if resource["kind"] == "KongPlugin"]
    for namespace in TENANTS:
        tenant_plugins = {
            item["plugin"] for item in plugins if item["metadata"]["namespace"] == namespace
        }
        expected_auth = "jwt" if namespace == "tenant-open-banking" else "key-auth"
        assert tenant_plugins == {expected_auth, "acl", "rate-limiting", "correlation-id"}


def test_synthetic_consumers_reference_credentials_by_name() -> None:
    resources = load_all("kubernetes/banklab/security/security-controls.yaml")
    consumers = [resource for resource in resources if resource["kind"] == "KongConsumer"]
    assert len(consumers) == 6
    assert all(consumer.get("credentials") for consumer in consumers)


def test_governance_policy_allows_only_reviewed_plugins() -> None:
    policy = load_all("kubernetes/banklab/governance/policy.yaml")[0]
    expression = policy["spec"]["validations"][0]["expression"]
    assert "request-transformer" not in expression
    assert "response-transformer" in expression
    assert policy["spec"]["failurePolicy"] == "Fail"


def test_admin_api_is_not_public() -> None:
    values = load_all("platform/kong/helm/values-kong-oss-baseline.yaml")[0]
    assert values["gateway"]["admin"]["type"] == "ClusterIP"
    assert values["gateway"]["admin"]["http"]["enabled"] is False
    assert values["gateway"]["admin"]["tls"]["enabled"] is True
    assert values["gateway"]["admin"]["ingress"]["enabled"] is False
