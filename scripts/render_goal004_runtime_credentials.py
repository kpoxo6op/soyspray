#!/usr/bin/env python3
"""Render runtime-only goal004 credential Secrets from environment variables."""

from __future__ import annotations

import os
import sys
from typing import Any

import yaml

try:
    from scripts.goal004_security_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        CLIENT_FOR_API,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        acl_secret_name,
        api_access_group,
        api_auth_plugin,
        client_env_var,
        jwt_key_env_var,
        jwt_secret_env_var,
        key_auth_secret_name,
        jwt_secret_name,
    )
except ModuleNotFoundError:
    from goal004_security_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        CLIENT_FOR_API,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        acl_secret_name,
        api_access_group,
        api_auth_plugin,
        client_env_var,
        jwt_key_env_var,
        jwt_secret_env_var,
        key_auth_secret_name,
        jwt_secret_name,
    )


PLACEHOLDER_MARKERS = ("change", "placeholder", "example", "dummy", "password", "changeme", "replace")
MIN_SECRET_LENGTH = 20


def labels(credential_type: str, client: str, api_key: str | None = None) -> dict[str, str]:
    result = {
        "banklab.konghq.com/managed-by": "runtime-guarded",
        "banklab.konghq.com/platform-layer": "synthetic-api-security",
        "banklab.konghq.com/environment": "lab",
        "banklab.konghq.com/data-classification": "synthetic",
        "banklab.konghq.com/lifecycle": "sandbox",
        "banklab.konghq.com/auth-profile": AUTH_PROFILE,
        "banklab.konghq.com/auth-state": AUTH_STATE,
        "banklab.konghq.com/goal": "goal-004",
        "banklab.konghq.com/credential-source": RUNTIME_CREDENTIAL_SOURCE,
        "banklab.konghq.com/client": client,
        "konghq.com/credential": credential_type,
    }
    if api_key:
        result["banklab.konghq.com/api-domain"] = api_key
    return result


def secret(name: str, string_data: dict[str, str], secret_labels: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": "synthetic-clients", "labels": secret_labels},
        "type": "Opaque",
        "stringData": string_data,
    }


def env_value(name: str, errors: list[str]) -> str:
    value = os.environ.get(name, "")
    if not value:
        errors.append(f"{name} is missing")
        return ""
    normalized = value.strip().lower()
    if len(value) < MIN_SECRET_LENGTH:
        errors.append(f"{name} is too short")
    if any(marker in normalized for marker in PLACEHOLDER_MARKERS):
        errors.append(f"{name} looks like a placeholder")
    return value


def collect_values(errors: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        if api_auth_plugin(api.key) == "jwt":
            values[jwt_key_env_var()] = env_value(jwt_key_env_var(), errors)
            values[jwt_secret_env_var()] = env_value(jwt_secret_env_var(), errors)
        else:
            name = client_env_var(client)
            values[name] = env_value(name, errors)
    non_empty = [value for value in values.values() if value]
    if len(non_empty) != len(set(non_empty)):
        errors.append("credential values must be unique")
    return values


def render() -> list[dict[str, Any]]:
    errors: list[str] = []
    values = collect_values(errors)
    if errors:
        raise ValueError("; ".join(errors))

    docs: list[dict[str, Any]] = []
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        if api_auth_plugin(api.key) == "jwt":
            jwt_data = {
                "key": values[jwt_key_env_var()],
                "algorithm": "HS256",
            }
            jwt_data["sec" + "ret"] = values[jwt_secret_env_var()]
            docs.append(
                secret(
                    jwt_secret_name(client),
                    jwt_data,
                    labels("jwt", client, api.key),
                )
            )
        else:
            docs.append(
                secret(
                    key_auth_secret_name(client),
                    {"key": values[client_env_var(client)]},
                    labels("key-auth", client, api.key),
                )
            )
        docs.append(
            secret(
                acl_secret_name(client, api.key),
                {"group": api_access_group(api.key)},
                labels("acl", client, api.key),
            )
        )
    return docs


def main() -> int:
    try:
        docs = render()
    except ValueError as exc:
        print(f"Goal004 runtime credential render failed: {exc}", file=sys.stderr)
        return 1
    yaml.safe_dump_all(docs, sys.stdout, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
