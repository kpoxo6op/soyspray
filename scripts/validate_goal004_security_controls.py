#!/usr/bin/env python3
"""Validate goal004 security controls locally."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.goal004_security_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        CLIENT_FOR_API,
        CLIENTS,
        CLIENT_API_ACCESS,
        CORRELATION_ID_HEADER,
        KONG_CONTROLLER_WEBHOOK_PORT,
        KUBE_API_SERVER_NODE_IPS,
        NODE_LOCAL_DNS_IP,
        REDIS_SERVICE_HOST,
        REDIS_SERVICE_PORT,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        acl_secret_name,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_profile,
        api_rate_limit_per_second,
        key_auth_secret_name,
        jwt_secret_name,
    )
    from scripts.render_goal004_security_controls import render
except ModuleNotFoundError:
    from goal004_security_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        CLIENT_FOR_API,
        CLIENTS,
        CLIENT_API_ACCESS,
        CORRELATION_ID_HEADER,
        KONG_CONTROLLER_WEBHOOK_PORT,
        KUBE_API_SERVER_NODE_IPS,
        NODE_LOCAL_DNS_IP,
        REDIS_SERVICE_HOST,
        REDIS_SERVICE_PORT,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        acl_secret_name,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_profile,
        api_rate_limit_per_second,
        key_auth_secret_name,
        jwt_secret_name,
    )
    from render_goal004_security_controls import render


REQUIRED_FILES = [
    "soydocs/kong-bank-lab/goals/goal-004-auth-rate-limit-security.md",
    "docs/runbooks/synthetic-api-security-apply-and-smoke.md",
    "platform/kong/security-controls/README.md",
    "platform/kong/security-controls/scripts/goal004-security-apply.sh",
    "platform/kong/security-controls/scripts/goal004-security-rollback.sh",
    "platform/kong/security-controls/scripts/goal004-rate-limit-test.sh",
    "scripts/goal004_security_config.py",
    "scripts/render_goal004_security_controls.py",
    "scripts/render_goal004_runtime_credentials.py",
    "scripts/validate_goal004_security_controls.py",
    "scripts/generate_goal004_smoke_plan.py",
]


def load_yaml(path: str | Path) -> Any:
    full = ROOT / path if isinstance(path, str) else path
    return yaml.safe_load(full.read_text(encoding="utf-8"))


def file_text(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def target_block(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:\n(?P<body>(?:\t.*\n|[ \t]*\n)*)", makefile, re.M)
    return match.group("body") if match else ""


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def rendered_docs() -> list[dict[str, Any]]:
    return render()


def docs_by_kind(docs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [doc for doc in docs if doc.get("kind") == kind]


def check_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        require((ROOT / relative).is_file(), errors, f"missing required goal004 file: {relative}")


def check_gate_precondition(errors: list[str]) -> None:
    require("Status: approved" in file_text("docs/decisions/goal-003-runtime-approval.md"), errors, "goal003 runtime approval must be approved")
    require("Ready for goal 004: yes" in file_text("reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md"), errors, "gate003 summary must allow goal004")


def check_metadata(errors: list[str]) -> None:
    exposure = load_yaml("apis/synthetic-bank/exposure-policy.yaml")
    require(exposure.get("authentication_required") == AUTH_STATE, errors, "exposure policy auth state mismatch")
    require(exposure.get("authorization_required") == AUTHORIZATION_PROFILE, errors, "exposure policy ACL mismatch")
    require(exposure.get("rate_limiting_required") == "goal004-redis-rate-limits", errors, "exposure policy rate limit mismatch")
    require(exposure.get("credential_source") == RUNTIME_CREDENTIAL_SOURCE, errors, "exposure policy credential source mismatch")

    routes = {route["api"]: route for route in load_yaml("apis/synthetic-bank/route-matrix.yaml")["routes"]}
    catalog = {entry["key"]: entry for entry in load_yaml("apis/synthetic-bank/api-catalog.yaml")["apis"]}
    for api in APIS:
        ownership = load_yaml(ROOT / "apis/synthetic-bank" / api.key / "ownership.yaml")
        for source_name, source in (("route matrix", routes[api.key]), ("catalog", catalog[api.key]), ("ownership", ownership)):
            require(source["auth_profile"] == AUTH_PROFILE, errors, f"{source_name} auth profile mismatch for {api.key}")
            require(source["auth_state"] == AUTH_STATE, errors, f"{source_name} auth state mismatch for {api.key}")
            require(source["auth_plugin"] == api_auth_plugin(api.key), errors, f"{source_name} auth plugin mismatch for {api.key}")
            require(source["authorization_profile"] == AUTHORIZATION_PROFILE, errors, f"{source_name} authorization mismatch for {api.key}")
            require(source["access_group"] == api_access_group(api.key), errors, f"{source_name} access group mismatch for {api.key}")
            require(source["rate_limit_profile"] == api_rate_limit_profile(api.exposure), errors, f"{source_name} rate profile mismatch for {api.key}")
        require(ownership["credential_source"] == RUNTIME_CREDENTIAL_SOURCE, errors, f"{api.key} credential source mismatch")

    clients = {client["client_name"]: client for client in load_yaml("clients/synthetic/client-catalog.yaml")["clients"]}
    require(set(clients) == set(CLIENTS), errors, "client catalog mismatch")
    for client, api_keys in CLIENT_API_ACCESS.items():
        entry = clients[client]
        require(tuple(entry["intended_apis"]) == api_keys, errors, f"{client} intended APIs mismatch")
        require(entry["credential_secret_namespace"] == "synthetic-clients", errors, f"{client} credential namespace mismatch")
        require(entry["credentials_created"] == RUNTIME_CREDENTIAL_SOURCE, errors, f"{client} credential source mismatch")


def check_rendered_controls(errors: list[str]) -> None:
    docs = rendered_docs()
    require(not docs_by_kind(docs, "Secret"), errors, "static goal004 renderer must not emit Secret resources")
    require(any(doc.get("kind") == "Namespace" and doc["metadata"]["name"] == "synthetic-clients" for doc in docs), errors, "synthetic-clients namespace missing")
    require(any(doc.get("kind") == "Deployment" and doc["metadata"]["name"] == "banklab-rate-limit-redis" for doc in docs), errors, "Redis Deployment missing")
    require(any(doc.get("kind") == "Service" and doc["metadata"]["name"] == "banklab-rate-limit-redis" for doc in docs), errors, "Redis Service missing")

    policies = {doc["metadata"]["name"]: doc for doc in docs_by_kind(docs, "NetworkPolicy")}
    require("banklab-rate-limit-redis-ingress" in policies, errors, "Redis ingress NetworkPolicy missing")
    require("kong-allow-rate-limit-redis" in policies, errors, "Kong Redis egress NetworkPolicy missing")
    require("kong-allow-node-local-dns" in policies, errors, "Kong NodeLocalDNS egress NetworkPolicy missing")
    require("kong-allow-controller-webhook-from-api-server" in policies, errors, "Kong controller webhook ingress NetworkPolicy missing")
    node_dns = policies.get("kong-allow-node-local-dns", {})
    node_dns_egress = node_dns.get("spec", {}).get("egress", [{}])[0]
    require(
        {"ipBlock": {"cidr": f"{NODE_LOCAL_DNS_IP}/32"}} in node_dns_egress.get("to", []),
        errors,
        "Kong NodeLocalDNS egress must target the node-local DNS IP",
    )
    webhook = policies.get("kong-allow-controller-webhook-from-api-server", {})
    webhook_ingress = webhook.get("spec", {}).get("ingress", [{}])[0]
    expected_api_servers = [{"ipBlock": {"cidr": f"{ip}/32"}} for ip in KUBE_API_SERVER_NODE_IPS]
    require(webhook_ingress.get("from") == expected_api_servers, errors, "Kong webhook ingress API-server source mismatch")
    require(
        {"protocol": "TCP", "port": KONG_CONTROLLER_WEBHOOK_PORT} in webhook_ingress.get("ports", []),
        errors,
        "Kong webhook ingress port mismatch",
    )

    plugins = docs_by_kind(docs, "KongPlugin")
    plugins_by_ns_name = {(doc["metadata"]["namespace"], doc["metadata"]["name"]): doc for doc in plugins}
    for api in APIS:
        auth_name = "banklab-jwt" if api_auth_plugin(api.key) == "jwt" else "banklab-key-auth"
        auth = plugins_by_ns_name.get((api.namespace, auth_name))
        require(auth is not None and auth["plugin"] == api_auth_plugin(api.key), errors, f"{api.key} auth plugin missing")
        if auth and auth["plugin"] == "key-auth":
            require(auth["config"]["key_names"] == ["apikey"], errors, f"{api.key} key-auth header mismatch")
            require(auth["config"]["hide_credentials"] is True, errors, f"{api.key} key-auth must hide credentials")
        if auth and auth["plugin"] == "jwt":
            require(auth["config"]["key_claim_name"] == "iss", errors, "JWT key claim mismatch")
            require(auth["config"]["claims_to_verify"] == ["exp"], errors, "JWT exp verification missing")
        acl = plugins_by_ns_name.get((api.namespace, "banklab-acl"))
        require(acl is not None and acl["config"]["allow"] == [api_access_group(api.key)], errors, f"{api.key} ACL mismatch")
        rate = plugins_by_ns_name.get((api.namespace, "banklab-rate-limit"))
        require(rate is not None and rate["plugin"] == "rate-limiting", errors, f"{api.key} rate plugin missing")
        if rate:
            require(rate["config"]["policy"] == "redis", errors, f"{api.key} rate policy must be redis")
            require(rate["config"]["second"] == api_rate_limit_per_second(api.exposure), errors, f"{api.key} rate second limit mismatch")
            require(rate["config"]["redis"]["host"] == REDIS_SERVICE_HOST, errors, f"{api.key} redis host mismatch")
            require(rate["config"]["redis"]["port"] == REDIS_SERVICE_PORT, errors, f"{api.key} redis port mismatch")
        corr = plugins_by_ns_name.get((api.namespace, "banklab-correlation-id"))
        require(corr is not None and corr["config"]["header_name"] == CORRELATION_ID_HEADER, errors, f"{api.key} correlation plugin mismatch")

    consumers = {doc["username"]: doc for doc in docs_by_kind(docs, "KongConsumer")}
    require(set(consumers) == set(CLIENT_FOR_API.values()), errors, "KongConsumer set mismatch")
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        expected_auth_secret = jwt_secret_name(client) if api_auth_plugin(api.key) == "jwt" else key_auth_secret_name(client)
        expected = [expected_auth_secret, acl_secret_name(client, api.key)]
        require(consumers[client]["metadata"]["namespace"] == "synthetic-clients", errors, f"{client} consumer namespace mismatch")
        require(consumers[client]["credentials"] == expected, errors, f"{client} credentials mismatch")

    routes = [doc for doc in docs_by_kind(docs, "HTTPRoute")]
    routes_by_name = {doc["metadata"]["name"]: doc for doc in routes}
    for api in APIS:
        route = routes_by_name[f"banklab-{api.key}"]
        require(route["metadata"]["annotations"]["konghq.com/plugins"] == api_plugin_annotation(api.key), errors, f"{api.key} route plugin annotation mismatch")


def check_makefile_and_ci(errors: list[str]) -> None:
    makefile = file_text("Makefile")
    ci = file_text(".github/workflows/ci.yml")
    for target in (
        "validate-goal004-security",
        "render-goal004-security",
        "goal004-static-test",
        "goal004-contract-test",
        "goal004-smoke-plan",
        "evidence-goal-004",
        "goal004-security-dry-run",
        "goal004-runtime-credentials-dry-run",
        "goal004-runtime-credentials-apply",
        "goal004-security-apply",
        "goal004-security-smoke",
        "goal004-security-negative-test",
        "goal004-rate-limit-test",
        "goal004-security-rollback",
        "goal004-runtime-ready",
    ):
        require(target_block(makefile, target), errors, f"missing Makefile target: {target}")
    for target in ("goal004-runtime-credentials-apply", "goal004-security-apply", "goal004-security-rollback"):
        require("require-cluster-mutation-permission.sh" in target_block(makefile, target) or "goal004-security" in target_block(makefile, target), errors, f"{target} must be guarded")
    require("make validate-goal004-security" in ci or "make validate-synthetic-api-security" in ci, errors, "CI must run goal004 local validation")
    for target in ("goal004-runtime-credentials-apply", "goal004-security-apply", "goal004-security-smoke", "goal004-rate-limit-test", "goal004-runtime-ready"):
        require(not re.search(rf"run:\s+make\s+{re.escape(target)}(?:\s|$)", ci), errors, f"CI must not run runtime target {target}")


def validate() -> list[str]:
    errors: list[str] = []
    check_required_files(errors)
    check_gate_precondition(errors)
    check_metadata(errors)
    check_rendered_controls(errors)
    check_makefile_and_ci(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Goal004 security validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Goal004 security validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
