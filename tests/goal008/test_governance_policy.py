from scripts.goal008_governance_policy_config import GOAL_ID, load_policy
from scripts.render_goal008_governance_policy import delete_resources, render
from scripts.render_goal008_governance_policy import fixture as render_fixture
from scripts.validate_goal008_governance_policy import EXPECTED_ALLOWED, validate


def docs(kind, rendered=None):
    rendered = render() if rendered is None else rendered
    return [doc for doc in rendered if doc.get("kind") == kind]


def test_policy_contract_allowlist():
    policy = load_policy()
    assert policy["goal_id"] == GOAL_ID
    assert set(policy["allowed_plugin_types"]) == EXPECTED_ALLOWED
    assert "request-transformer" in set(policy["denied_plugin_types"])
    assert not (set(policy["allowed_plugin_types"]) & set(policy["denied_plugin_types"]))


def test_rendered_admission_policy_fail_closed():
    policy = docs("ValidatingAdmissionPolicy")[0]
    assert policy["spec"]["failurePolicy"] == "Fail"
    expression = policy["spec"]["validations"][0]["expression"]
    for plugin in EXPECTED_ALLOWED:
        assert f"'{plugin}'" in expression
    assert "'request-transformer'" not in expression


def test_rendered_binding_enforces_deny():
    binding = docs("ValidatingAdmissionPolicyBinding")[0]
    assert binding["spec"]["validationActions"] == ["Deny"]


def test_fixtures_model_safe_and_unsafe_plugins():
    policy = load_policy()
    safe = render_fixture(policy["safe_fixture"])[0]
    unsafe = render_fixture(policy["unsafe_fixture"])[0]
    assert safe["plugin"] == "response-transformer"
    assert unsafe["plugin"] == "request-transformer"
    assert safe["metadata"]["namespace"] == unsafe["metadata"]["namespace"] == "tenant-accounts"


def test_delete_render_removes_binding_before_policy():
    rendered = delete_resources()
    assert [doc["kind"] for doc in rendered] == ["ValidatingAdmissionPolicyBinding", "ValidatingAdmissionPolicy"]


def test_goal008_validator_passes():
    assert validate() == []
