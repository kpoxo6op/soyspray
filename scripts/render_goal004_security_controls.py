#!/usr/bin/env python3
"""Render non-secret goal004 security-control resources."""

from __future__ import annotations

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
        CORRELATION_ID_HEADER,
        REDIS_SERVICE_HOST,
        REDIS_SERVICE_PORT,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        acl_secret_name,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_per_second,
        key_auth_secret_name,
        jwt_secret_name,
    )
except ModuleNotFoundError:
    from goal004_security_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        CLIENT_FOR_API,
        CORRELATION_ID_HEADER,
        REDIS_SERVICE_HOST,
        REDIS_SERVICE_PORT,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        acl_secret_name,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_per_second,
        key_auth_secret_name,
        jwt_secret_name,
    )


def labels(extra: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "banklab.konghq.com/managed-by": "gitops",
        "banklab.konghq.com/platform-layer": "synthetic-api-security",
        "banklab.konghq.com/environment": "lab",
        "banklab.konghq.com/data-classification": "synthetic",
        "banklab.konghq.com/lifecycle": "sandbox",
        "banklab.konghq.com/auth-profile": AUTH_PROFILE,
        "banklab.konghq.com/auth-state": AUTH_STATE,
        "banklab.konghq.com/goal": "goal-004",
    }
    if extra:
        base.update(extra)
    return base


def namespace() -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": "synthetic-clients",
            "labels": labels({"banklab.konghq.com/platform-layer": "synthetic-client-security"}),
        },
    }


def redis_deployment() -> dict[str, Any]:
    pod_labels = labels({"app.kubernetes.io/name": "banklab-rate-limit-redis", "banklab.konghq.com/component": "rate-limit-redis"})
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "banklab-rate-limit-redis", "namespace": "platform-kong", "labels": pod_labels},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app.kubernetes.io/name": "banklab-rate-limit-redis"}},
            "template": {
                "metadata": {"labels": pod_labels},
                "spec": {
                    "containers": [
                        {
                            "name": "redis",
                            "image": "redis:7.4.2-alpine",
                            "args": ["redis-server", "--save", "", "--appendonly", "no"],
                            "ports": [{"name": "redis", "containerPort": REDIS_SERVICE_PORT}],
                            "resources": {
                                "requests": {"cpu": "25m", "memory": "64Mi"},
                                "limits": {"cpu": "100m", "memory": "128Mi"},
                            },
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "runAsNonRoot": True,
                                "runAsUser": 999,
                                "capabilities": {"drop": ["ALL"]},
                            },
                            "volumeMounts": [{"name": "redis-tmp", "mountPath": "/data"}],
                        }
                    ],
                    "volumes": [{"name": "redis-tmp", "emptyDir": {}}],
                },
            },
        },
    }


def redis_service() -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "banklab-rate-limit-redis", "namespace": "platform-kong", "labels": labels()},
        "spec": {
            "type": "ClusterIP",
            "selector": {"app.kubernetes.io/name": "banklab-rate-limit-redis"},
            "ports": [{"name": "redis", "port": REDIS_SERVICE_PORT, "targetPort": "redis"}],
        },
    }


def redis_ingress_policy() -> dict[str, Any]:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "banklab-rate-limit-redis-ingress", "namespace": "platform-kong", "labels": labels()},
        "spec": {
            "podSelector": {"matchLabels": {"app.kubernetes.io/name": "banklab-rate-limit-redis"}},
            "policyTypes": ["Ingress"],
            "ingress": [
                {
                    "from": [{"podSelector": {"matchLabels": {"banklab.konghq.com/component": "gateway"}}}],
                    "ports": [{"protocol": "TCP", "port": REDIS_SERVICE_PORT}],
                }
            ],
        },
    }


def kong_redis_egress_policy() -> dict[str, Any]:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "kong-allow-rate-limit-redis", "namespace": "platform-kong", "labels": labels()},
        "spec": {
            "podSelector": {"matchLabels": {"banklab.konghq.com/component": "gateway"}},
            "policyTypes": ["Egress"],
            "egress": [
                {
                    "to": [{"podSelector": {"matchLabels": {"app.kubernetes.io/name": "banklab-rate-limit-redis"}}}],
                    "ports": [{"protocol": "TCP", "port": REDIS_SERVICE_PORT}],
                }
            ],
        },
    }


def plugin(name: str, namespace_name: str, api_key: str, plugin_name: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "apiVersion": "configuration.konghq.com/v1",
        "kind": "KongPlugin",
        "metadata": {
            "name": name,
            "namespace": namespace_name,
            "annotations": {"kubernetes.io/ingress.class": "kong"},
            "labels": labels({"banklab.konghq.com/api-domain": api_key}),
        },
        "plugin": plugin_name,
        "config": config,
    }


def plugins_for_api(api: Any) -> list[dict[str, Any]]:
    auth_plugins: list[dict[str, Any]] = []
    if api_auth_plugin(api.key) == "jwt":
        auth_plugins.append(
            plugin(
                "banklab-jwt",
                api.namespace,
                api.key,
                "jwt",
                {
                    "key_claim_name": "iss",
                    "claims_to_verify": ["exp"],
                    "secret_is_base64": False,
                    "run_on_preflight": False,
                },
            )
        )
    else:
        auth_plugins.append(
            plugin(
                "banklab-key-auth",
                api.namespace,
                api.key,
                "key-auth",
                {
                    "key_names": ["apikey"],
                    "key_in_header": True,
                    "key_in_query": False,
                    "key_in_body": False,
                    "hide_credentials": True,
                    "run_on_preflight": False,
                },
            )
        )
    common = [
        plugin(
            "banklab-acl",
            api.namespace,
            api.key,
            "acl",
            {"allow": [api_access_group(api.key)], "hide_groups_header": True},
        ),
        plugin(
            "banklab-rate-limit",
            api.namespace,
            api.key,
            "rate-limiting",
            {
                "policy": "redis",
                "limit_by": "consumer",
                "second": api_rate_limit_per_second(api.exposure),
                "fault_tolerant": False,
                "hide_client_headers": False,
                "redis": {
                    "host": REDIS_SERVICE_HOST,
                    "port": REDIS_SERVICE_PORT,
                    "database": 0,
                    "timeout": 2000,
                },
            },
        ),
        plugin(
            "banklab-correlation-id",
            api.namespace,
            api.key,
            "correlation-id",
            {"header_name": CORRELATION_ID_HEADER, "generator": "uuid", "echo_downstream": True},
        ),
    ]
    return auth_plugins + common


def consumer_for_api(api: Any) -> dict[str, Any]:
    client = CLIENT_FOR_API[api.key]
    credentials = [acl_secret_name(client, api.key)]
    credentials.insert(0, jwt_secret_name(client) if api_auth_plugin(api.key) == "jwt" else key_auth_secret_name(client))
    return {
        "apiVersion": "configuration.konghq.com/v1",
        "kind": "KongConsumer",
        "metadata": {
            "name": client,
            "namespace": "synthetic-clients",
            "annotations": {"kubernetes.io/ingress.class": "kong"},
            "labels": labels({"banklab.konghq.com/credential-source": RUNTIME_CREDENTIAL_SOURCE}),
        },
        "username": client,
        "credentials": credentials,
    }


def route_for_api(api: Any) -> dict[str, Any]:
    route_file = "httproute-external.yaml" if api.exposure == "external" else "httproute-internal.yaml"
    route = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / route_file).read_text(encoding="utf-8"))
    route.setdefault("metadata", {}).setdefault("annotations", {})["konghq.com/plugins"] = api_plugin_annotation(api.key)
    return route


def render() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = [
        namespace(),
        redis_deployment(),
        redis_service(),
        redis_ingress_policy(),
        kong_redis_egress_policy(),
    ]
    for api in APIS:
        docs.extend(plugins_for_api(api))
    docs.extend(consumer_for_api(api) for api in APIS)
    docs.extend(route_for_api(api) for api in APIS)
    return docs


def main() -> int:
    yaml.safe_dump_all(render(), sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
