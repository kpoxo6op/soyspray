#!/usr/bin/env python3
"""Validate goal008 Kong governance policy resources and fixtures."""

from __future__ import annotations

import sys
from typing import Any

try:
    from scripts.goal008_governance_policy_config import GOAL_ID, load_policy
    from scripts.render_goal008_governance_policy import delete_resources, render
    from scripts.render_goal008_governance_policy import fixture as render_fixture
except ModuleNotFoundError:
    from goal008_governance_policy_config import GOAL_ID, load_policy
    from render_goal008_governance_policy import delete_resources, render
    from render_goal008_governance_policy import fixture as render_fixture


EXPECTED_ALLOWED = {"acl", "correlation-id", "jwt", "key-auth", "rate-limiting", "response-transformer"}
FORBIDDEN_MANAGED = {"pre-function", "post-function", "request-transformer", "file-log", "syslog"}


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def docs_by_kind(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc.get("kind") == kind]


def validate() -> list[str]:
    errors: list[str] = []
    policy = load_policy()
    allowed = set(policy.get("allowed_plugin_types", []))
    denied = set(policy.get("denied_plugin_types", []))

    require(policy.get("goal_id") == GOAL_ID, errors, "goal_id mismatch")
    require(policy.get("runtime_kind") == "ValidatingAdmissionPolicy", errors, "runtime_kind mismatch")
    require(policy.get("failure_policy") == "Fail", errors, "failurePolicy must fail closed")
    require(policy.get("validation_action") == "Deny", errors, "binding must enforce Deny")
    require(allowed == EXPECTED_ALLOWED, errors, "allowed plugin allowlist mismatch")
    require(FORBIDDEN_MANAGED <= denied, errors, "denied plugin examples must include unsafe managed plugins")
    require(not (allowed & denied), errors, "allowed and denied plugin sets must not overlap")

    rendered = render()
    vap = docs_by_kind(rendered, "ValidatingAdmissionPolicy")
    binding = docs_by_kind(rendered, "ValidatingAdmissionPolicyBinding")
    require(len(vap) == 1, errors, "must render one ValidatingAdmissionPolicy")
    require(len(binding) == 1, errors, "must render one ValidatingAdmissionPolicyBinding")
    if vap:
        spec = vap[0]["spec"]
        require(spec["failurePolicy"] == "Fail", errors, "rendered policy must fail closed")
        expression = spec["validations"][0]["expression"]
        for plugin in allowed:
            require(f"'{plugin}'" in expression, errors, f"rendered expression missing {plugin}")
        require("request-transformer" not in expression, errors, "unsafe plugin must not appear in allow expression")
    if binding:
        require(binding[0]["spec"]["validationActions"] == ["Deny"], errors, "binding validationActions mismatch")

    safe = render_fixture(policy["safe_fixture"])
    unsafe = render_fixture(policy["unsafe_fixture"])
    require(safe[0]["plugin"] in allowed, errors, "safe fixture plugin must be allowed")
    require(unsafe[0]["plugin"] in denied, errors, "unsafe fixture plugin must be denied")
    require(safe[0]["metadata"]["namespace"] == unsafe[0]["metadata"]["namespace"] == "tenant-accounts", errors, "fixtures must target tenant-accounts")

    delete_docs = delete_resources()
    require([doc["kind"] for doc in delete_docs] == ["ValidatingAdmissionPolicyBinding", "ValidatingAdmissionPolicy"], errors, "delete order must remove binding before policy")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"goal008 validation failed: {error}", file=sys.stderr)
        return 1
    print("goal008 governance policy validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
