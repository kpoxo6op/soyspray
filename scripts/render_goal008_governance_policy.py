#!/usr/bin/env python3
"""Render goal008 Kubernetes-native Kong governance policy resources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.goal008_governance_policy_config import GOAL_LABEL, POLICY_PATH, load_policy, relative
    from scripts.synthetic_bank_config import ROOT
except ModuleNotFoundError:
    from goal008_governance_policy_config import GOAL_LABEL, POLICY_PATH, load_policy, relative
    from synthetic_bank_config import ROOT


LABEL_PREFIX = "platform.soyspray.io"


def labels() -> dict[str, str]:
    return {
        f"{LABEL_PREFIX}/managed-by": "gitops",
        f"{LABEL_PREFIX}/goal": GOAL_LABEL,
        f"{LABEL_PREFIX}/control-plane": "governance",
        f"{LABEL_PREFIX}/policy-id": load_policy()["policy_id"],
    }


def annotations() -> dict[str, str]:
    policy = load_policy()
    return {
        f"{LABEL_PREFIX}/policy-file": relative(POLICY_PATH),
        f"{LABEL_PREFIX}/runbook": policy["runbook"],
    }


def policy_expression(allowed: list[str]) -> str:
    allowed_list = ", ".join(f"'{plugin}'" for plugin in allowed)
    return f"object.plugin in [{allowed_list}]"


def validating_admission_policy() -> dict[str, Any]:
    policy = load_policy()
    match = policy["match"]
    return {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingAdmissionPolicy",
        "metadata": {
            "name": policy["admission_policy_name"],
            "labels": labels(),
            "annotations": annotations(),
        },
        "spec": {
            "failurePolicy": policy["failure_policy"],
            "matchConstraints": {
                "resourceRules": [
                    {
                        "apiGroups": [match["api_group"]],
                        "apiVersions": [match["api_version"]],
                        "operations": match["operations"],
                        "resources": [match["resource"]],
                    }
                ]
            },
            "validations": [
                {
                    "expression": policy_expression(policy["allowed_plugin_types"]),
                    "message": "KongPlugin plugin must be approved by the banklab Kong governance allowlist.",
                    "reason": "Forbidden",
                }
            ],
        },
    }


def validating_admission_policy_binding() -> dict[str, Any]:
    policy = load_policy()
    return {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingAdmissionPolicyBinding",
        "metadata": {
            "name": policy["admission_binding_name"],
            "labels": labels(),
            "annotations": annotations(),
        },
        "spec": {
            "policyName": policy["admission_policy_name"],
            "validationActions": [policy["validation_action"]],
        },
    }


def render() -> list[dict[str, Any]]:
    return [validating_admission_policy(), validating_admission_policy_binding()]


def delete_resources() -> list[dict[str, Any]]:
    policy = load_policy()
    return [
        {
            "apiVersion": "admissionregistration.k8s.io/v1",
            "kind": "ValidatingAdmissionPolicyBinding",
            "metadata": {"name": policy["admission_binding_name"], "labels": labels()},
        },
        {
            "apiVersion": "admissionregistration.k8s.io/v1",
            "kind": "ValidatingAdmissionPolicy",
            "metadata": {"name": policy["admission_policy_name"], "labels": labels()},
        },
    ]


def fixture(path: str) -> list[dict[str, Any]]:
    loaded = list(yaml.safe_load_all((ROOT / path).read_text(encoding="utf-8")))
    return [doc for doc in loaded if doc]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="render metadata-only resources for deletion")
    parser.add_argument("--safe-fixture", action="store_true", help="render the allowed server-dry-run fixture")
    parser.add_argument("--unsafe-fixture", action="store_true", help="render the denied server-dry-run fixture")
    args = parser.parse_args()
    policy = load_policy()
    if args.safe_fixture:
        docs = fixture(policy["safe_fixture"])
    elif args.unsafe_fixture:
        docs = fixture(policy["unsafe_fixture"])
    else:
        docs = delete_resources() if args.delete else render()
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
