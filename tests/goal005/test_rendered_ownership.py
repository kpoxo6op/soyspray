from scripts.goal005_tenancy_config import SAMPLE_CHANGE_PLUGIN_NAME
from scripts.render_goal005_change import render as render_change, rollback_resources
from scripts.render_goal005_tenancy_rbac import render as render_tenancy
from scripts.validate_rendered_ownership import validate


def test_goal005_tenancy_overlay_renders():
    assert render_tenancy()


def test_goal005_normal_change_overlay_renders():
    assert render_change()


def test_goal005_rollback_overlay_renders():
    assert rollback_resources()


def test_kong_facing_resources_include_ownership_metadata():
    docs = [*render_tenancy(), *render_change()]
    for doc in docs:
        if doc.get("kind") not in {"HTTPRoute", "KongPlugin"}:
            continue
        labels = doc["metadata"]["labels"]
        annotations = doc["metadata"].get("annotations", {})
        assert "platform.soyspray.io/tenant" in labels
        assert "platform.soyspray.io/api-id" in labels
        assert "platform.soyspray.io/logical-workspace" in labels
        assert "platform.soyspray.io/exposure" in labels
        assert "platform.soyspray.io/data-classification" in labels
        assert labels["platform.soyspray.io/managed-by"] == "gitops"
        assert "platform.soyspray.io/change-class" in labels
        assert "platform.soyspray.io/runbook" in annotations


def test_tenant_resources_are_namespaced_and_safe():
    docs = [*render_tenancy(), *render_change()]
    assert not [doc for doc in docs if doc.get("kind") == "Secret"]
    assert not [doc for doc in docs if doc.get("kind") == "KongClusterPlugin"]
    assert not [doc for doc in docs if doc.get("kind") == "NetworkPolicy"]
    for doc in docs:
        if doc.get("kind") in {"HTTPRoute", "KongPlugin", "Role", "RoleBinding", "ServiceAccount"}:
            assert doc["metadata"].get("namespace")


def test_sample_change_is_route_scoped_not_global():
    docs = render_change()
    route = next(doc for doc in docs if doc.get("kind") == "HTTPRoute")
    plugin = next(doc for doc in docs if doc.get("kind") == "KongPlugin")
    assert plugin["metadata"]["namespace"] == route["metadata"]["namespace"]
    assert SAMPLE_CHANGE_PLUGIN_NAME in route["metadata"]["annotations"]["konghq.com/plugins"]


def test_rendered_ownership_validator_passes():
    assert validate() == []
