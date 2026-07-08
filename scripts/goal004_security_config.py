"""Goal 004 security-control matrix."""

from __future__ import annotations

try:
    from scripts.synthetic_bank_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        CLIENT_API_ACCESS,
        CLIENTS,
        CORRELATION_ID_HEADER,
        EXTERNAL_RATE_LIMIT_PROFILE,
        EXTERNAL_RATE_LIMIT_PER_SECOND,
        INTERNAL_RATE_LIMIT_PROFILE,
        INTERNAL_RATE_LIMIT_PER_SECOND,
        REDIS_SERVICE_HOST,
        REDIS_SERVICE_PORT,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_profile,
        api_rate_limit_per_second,
        client_env_var,
        jwt_key_env_var,
        jwt_secret_env_var,
    )
except ModuleNotFoundError:
    from synthetic_bank_config import (
        APIS,
        AUTH_PROFILE,
        AUTH_STATE,
        AUTHORIZATION_PROFILE,
        CLIENT_API_ACCESS,
        CLIENTS,
        CORRELATION_ID_HEADER,
        EXTERNAL_RATE_LIMIT_PROFILE,
        EXTERNAL_RATE_LIMIT_PER_SECOND,
        INTERNAL_RATE_LIMIT_PROFILE,
        INTERNAL_RATE_LIMIT_PER_SECOND,
        REDIS_SERVICE_HOST,
        REDIS_SERVICE_PORT,
        ROOT,
        RUNTIME_CREDENTIAL_SOURCE,
        api_access_group,
        api_auth_plugin,
        api_plugin_annotation,
        api_rate_limit_profile,
        api_rate_limit_per_second,
        client_env_var,
        jwt_key_env_var,
        jwt_secret_env_var,
    )


CLIENT_FOR_API = {
    "accounts": "mobile-banking-app",
    "payments": "payments-processor",
    "cards": "internet-banking-web",
    "customer-profile": "internal-crm",
    "fraud-decisions": "fraud-platform",
    "open-banking": "external-fintech-partner",
}


def key_auth_secret_name(client: str) -> str:
    return f"banklab-{client}-key-auth"


def jwt_secret_name(client: str) -> str:
    return f"banklab-{client}-jwt"


def acl_secret_name(client: str, api_key: str) -> str:
    return f"banklab-{client}-{api_key}-acl"
