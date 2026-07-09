#!/usr/bin/env python3
"""Validate Goal010 read-only drift guard contracts."""

from __future__ import annotations

import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from scripts.goal010_drift_guard_config import (
        ACCOUNTS_ROUTE_PLUGINS,
        DENIED_PLUGIN_TYPE,
        EXPECTED_CONTEXT,
        FINAL_APPROVAL_CANDIDATE_PATH,
        GOAL008_POLICY_NAME,
        GOAL009_PLUGIN_NAME,
        GOAL_BODY_PATH,
        GOAL_ID,
        HANDOVER_PATH,
        INVENTORY_PATH,
        RUNTIME_APPROVAL_PATH,
        RUNTIME_SCRIPT_PATHS,
        load_inventory,
    )
except ModuleNotFoundError:
    from goal010_drift_guard_config import (
        ACCOUNTS_ROUTE_PLUGINS,
        DENIED_PLUGIN_TYPE,
        EXPECTED_CONTEXT,
        FINAL_APPROVAL_CANDIDATE_PATH,
        GOAL008_POLICY_NAME,
        GOAL009_PLUGIN_NAME,
        GOAL_BODY_PATH,
        GOAL_ID,
        HANDOVER_PATH,
        INVENTORY_PATH,
        RUNTIME_APPROVAL_PATH,
        RUNTIME_SCRIPT_PATHS,
        load_inventory,
    )


MUTATING_KUBECTL_PATTERN = re.compile(r"\bkubectl\b[^\n]*\b(apply|delete|patch|annotate|label|replace|create|scale|rollout|drain|cordon|uncordon)\b")
MUTATING_ADMIN_PATTERN = re.compile(r"\bcurl\b[^\n]*(?:-X|--request)[= ]*(POST|PUT|PATCH|DELETE)\b", re.IGNORECASE)
RAW_SECRET_MARKERS = ("BANKLAB_MOBILE_BANKING_APP_API_KEY=", "BANKLAB_INTERNET_BANKING_WEB_API_KEY=")


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def route_plugins(inventory: dict[str, Any]) -> list[str]:
    annotation = inventory.get("accounts_route", {}).get("plugin_annotation", "")
    return [plugin.strip() for plugin in annotation.split(",") if plugin.strip()]


def expected_plugins(inventory: dict[str, Any]) -> dict[str, str]:
    return {entry["name"]: entry["plugin"] for entry in inventory.get("expected_kong_plugins", [])}


def validate_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    route = inventory.get("accounts_route", {})
    absent = inventory.get("expected_absent", {})
    plugin_types = set(inventory.get("approved_plugin_types", []))
    denied_types = set(inventory.get("denied_plugin_types", []))
    plugins = expected_plugins(inventory)
    route_plugin_list = route_plugins(inventory)

    require(inventory.get("goal_id") == GOAL_ID, errors, "goal_id mismatch")
    require(inventory.get("kubernetes_context") == EXPECTED_CONTEXT, errors, "expected Kubernetes context mismatch")
    require("tenant-accounts" in inventory.get("namespaces", []), errors, "tenant-accounts namespace missing")
    require(route.get("kind") == "HTTPRoute", errors, "accounts route kind must be HTTPRoute")
    require(route.get("namespace") == "tenant-accounts", errors, "accounts route namespace mismatch")
    require(route.get("name") == "banklab-accounts", errors, "accounts route name mismatch")
    require(route.get("plugin_annotation") == ACCOUNTS_ROUTE_PLUGINS, errors, "accounts route plugin annotation mismatch")
    for required in ("banklab-key-auth", "banklab-acl", "banklab-rate-limit", "banklab-correlation-id"):
        require(required in route_plugin_list, errors, f"accounts route missing {required}")
        require(required in plugins, errors, f"expected KongPlugin inventory missing {required}")
    require(plugins.get("banklab-key-auth") == "key-auth", errors, "banklab-key-auth plugin type mismatch")
    require(plugins.get("banklab-acl") == "acl", errors, "banklab-acl plugin type mismatch")
    require(plugins.get("banklab-rate-limit") == "rate-limiting", errors, "banklab-rate-limit plugin type mismatch")
    require(plugins.get("banklab-correlation-id") == "correlation-id", errors, "banklab-correlation-id plugin type mismatch")
    require(DENIED_PLUGIN_TYPE in denied_types, errors, "request-transformer must be denied")
    require(DENIED_PLUGIN_TYPE not in plugin_types, errors, "request-transformer must not be approved")
    require(GOAL009_PLUGIN_NAME not in route_plugin_list, errors, "goal009 plugin must not be in route annotation")
    require(GOAL009_PLUGIN_NAME in absent.get("kong_plugins", []), errors, "goal009 KongPlugin absence must be expected")
    require(GOAL009_PLUGIN_NAME in absent.get("annotation_references", []), errors, "goal009 annotation absence must be expected")
    absent_admission = {(entry.get("kind"), entry.get("name")) for entry in absent.get("admission_resources", [])}
    require(("ValidatingAdmissionPolicy", GOAL008_POLICY_NAME) in absent_admission, errors, "goal008 admission policy absence missing")
    require(("ValidatingAdmissionPolicyBinding", GOAL008_POLICY_NAME) in absent_admission, errors, "goal008 admission binding absence missing")
    require("KongClusterPlugin" in absent.get("global_plugin_kinds", []), errors, "global KongPlugin attachment must be rejected")
    return errors


def validate_script_text(text: str) -> list[str]:
    errors: list[str] = []
    require(not MUTATING_KUBECTL_PATTERN.search(text), errors, "runtime script contains a mutating kubectl command")
    require(not MUTATING_ADMIN_PATTERN.search(text), errors, "runtime script contains a mutating Kong Admin API call")
    return errors


def redacted_report(text: str) -> str:
    redacted = text
    for marker in RAW_SECRET_MARKERS:
        key = marker.split("=", 1)[0]
        redacted = re.sub(rf"{re.escape(key)}=[^\s]+", f"{key}=<redacted>", redacted)
    return redacted


def negative_inventory_fixture(kind: str) -> dict[str, Any]:
    inventory = deepcopy(load_inventory())
    if kind == "missing-key-auth":
        inventory["accounts_route"]["plugin_annotation"] = "banklab-acl,banklab-rate-limit,banklab-correlation-id"
    elif kind == "missing-acl":
        inventory["accounts_route"]["plugin_annotation"] = "banklab-key-auth,banklab-rate-limit,banklab-correlation-id"
    elif kind == "missing-rate-limit":
        inventory["accounts_route"]["plugin_annotation"] = "banklab-key-auth,banklab-acl,banklab-correlation-id"
    elif kind == "missing-correlation-id":
        inventory["accounts_route"]["plugin_annotation"] = "banklab-key-auth,banklab-acl,banklab-rate-limit"
    elif kind == "goal009-plugin":
        inventory["accounts_route"]["plugin_annotation"] = ACCOUNTS_ROUTE_PLUGINS + ",banklab-goal009-security-headers"
    elif kind == "request-transformer":
        inventory["expected_kong_plugins"][0]["plugin"] = "request-transformer"
        inventory["approved_plugin_types"].append("request-transformer")
    elif kind == "global-plugin":
        inventory["expected_absent"]["global_plugin_kinds"] = []
    elif kind == "goal008-admission":
        inventory["expected_absent"]["admission_resources"] = []
    else:
        raise ValueError(kind)
    return inventory


def validate() -> list[str]:
    errors: list[str] = []
    require(INVENTORY_PATH.is_file(), errors, "expected inventory file missing")
    inventory = load_inventory()
    errors.extend(validate_inventory(inventory))

    for fixture in (
        "missing-key-auth",
        "missing-acl",
        "missing-rate-limit",
        "missing-correlation-id",
        "goal009-plugin",
        "request-transformer",
        "global-plugin",
        "goal008-admission",
    ):
        require(validate_inventory(negative_inventory_fixture(fixture)), errors, f"negative fixture {fixture} unexpectedly passed")

    for path in RUNTIME_SCRIPT_PATHS:
        require(path.is_file(), errors, f"runtime script missing: {path}")
        if path.is_file():
            errors.extend(f"{path.name}: {error}" for error in validate_script_text(path.read_text(encoding="utf-8")))

    for path in (GOAL_BODY_PATH, RUNTIME_APPROVAL_PATH, FINAL_APPROVAL_CANDIDATE_PATH):
        require(path.is_file(), errors, f"required Goal010 document missing or not reserved: {path}")
    require(HANDOVER_PATH.parent.is_dir(), errors, "handover directory missing")

    approval_text = RUNTIME_APPROVAL_PATH.read_text(encoding="utf-8") if RUNTIME_APPROVAL_PATH.is_file() else ""
    final_text = FINAL_APPROVAL_CANDIDATE_PATH.read_text(encoding="utf-8") if FINAL_APPROVAL_CANDIDATE_PATH.is_file() else ""
    require("Status: pending approval" in approval_text or "Status: approved" in approval_text, errors, "Goal010 approval file status missing")
    require("Status: pending final approval" in final_text, errors, "final approval candidate must remain pending")
    require(redacted_report("BANKLAB_MOBILE_BANKING_APP_API_KEY=secret") != "BANKLAB_MOBILE_BANKING_APP_API_KEY=secret", errors, "report redaction helper failed")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"goal010 validation failed: {error}", file=sys.stderr)
        return 1
    print("goal010 drift guard validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
