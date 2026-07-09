from copy import deepcopy

from scripts.goal010_drift_guard_config import (
    ACCOUNTS_ROUTE_PLUGINS,
    EXPECTED_CONTEXT,
    GOAL008_POLICY_NAME,
    GOAL009_PLUGIN_NAME,
    GOAL_ID,
    load_inventory,
)
from scripts.validate_goal010_drift_guard import (
    redacted_report,
    validate,
    validate_inventory,
    validate_script_text,
)


def test_expected_inventory_schema_is_stable():
    inventory = load_inventory()
    assert inventory["goal_id"] == GOAL_ID
    assert inventory["kubernetes_context"] == EXPECTED_CONTEXT
    assert inventory["mutation_mode"] == "disabled"
    assert inventory["accounts_route"]["kind"] == "HTTPRoute"
    assert inventory["accounts_route"]["namespace"] == "tenant-accounts"
    assert inventory["accounts_route"]["name"] == "banklab-accounts"
    assert inventory["accounts_route"]["plugin_annotation"] == ACCOUNTS_ROUTE_PLUGINS
    assert inventory["reports"]["summary"] == "reports/goal-010-summary.md"


def test_expected_inventory_names_plugins_and_absences():
    inventory = load_inventory()
    plugins = {entry["name"]: entry["plugin"] for entry in inventory["expected_kong_plugins"]}
    assert plugins["banklab-key-auth"] == "key-auth"
    assert plugins["banklab-acl"] == "acl"
    assert plugins["banklab-rate-limit"] == "rate-limiting"
    assert plugins["banklab-correlation-id"] == "correlation-id"
    assert "request-transformer" in inventory["denied_plugin_types"]
    assert GOAL009_PLUGIN_NAME in inventory["expected_absent"]["kong_plugins"]
    admission_absent = {(entry["kind"], entry["name"]) for entry in inventory["expected_absent"]["admission_resources"]}
    assert ("ValidatingAdmissionPolicy", GOAL008_POLICY_NAME) in admission_absent
    assert ("ValidatingAdmissionPolicyBinding", GOAL008_POLICY_NAME) in admission_absent


def inventory_without(plugin_name):
    inventory = deepcopy(load_inventory())
    plugins = [plugin for plugin in inventory["accounts_route"]["required_plugins"] if plugin != plugin_name]
    inventory["accounts_route"]["required_plugins"] = plugins
    inventory["accounts_route"]["plugin_annotation"] = ",".join(plugins)
    return inventory


def test_negative_missing_route_plugins_fail_validation():
    for plugin in ("banklab-key-auth", "banklab-acl", "banklab-rate-limit", "banklab-correlation-id"):
        errors = validate_inventory(inventory_without(plugin))
        assert errors, plugin


def test_negative_goal009_plugin_reference_fails_validation():
    inventory = deepcopy(load_inventory())
    inventory["accounts_route"]["plugin_annotation"] = ACCOUNTS_ROUTE_PLUGINS + ",banklab-goal009-security-headers"
    assert validate_inventory(inventory)


def test_negative_request_transformer_fails_validation():
    inventory = deepcopy(load_inventory())
    inventory["expected_kong_plugins"][0]["plugin"] = "request-transformer"
    inventory["approved_plugin_types"].append("request-transformer")
    assert validate_inventory(inventory)


def test_negative_global_plugin_fixture_fails_validation():
    inventory = deepcopy(load_inventory())
    inventory["expected_absent"]["global_plugin_kinds"] = []
    assert validate_inventory(inventory)


def test_negative_goal008_admission_fixture_fails_validation():
    inventory = deepcopy(load_inventory())
    inventory["expected_absent"]["admission_resources"] = []
    assert validate_inventory(inventory)


def test_runtime_script_mutation_guards():
    for command in ("kubectl apply", "kubectl delete", "kubectl patch", "kubectl annotate", "kubectl label"):
        assert validate_script_text(command)
    assert validate_script_text("curl --request POST http://kong-admin.local/plugins")
    assert validate_script_text("curl -X DELETE http://kong-admin.local/plugins/foo")
    assert validate_script_text("kubectl get kongplugin -A") == []


def test_report_redaction_and_format_contracts():
    redacted = redacted_report("BANKLAB_MOBILE_BANKING_APP_API_KEY=secret")
    assert "secret" not in redacted
    assert "<redacted>" in redacted
    inventory = load_inventory()
    for key in ("summary", "readiness", "inventory", "drift", "behavior", "no_mutation", "rollback"):
        assert inventory["reports"][key].startswith("reports/goal-010-")


def test_goal010_validator_passes():
    assert validate() == []
