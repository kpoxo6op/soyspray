import os
import subprocess
import sys

import yaml

from scripts.goal004_security_config import APIS, CLIENT_FOR_API, ROOT, acl_secret_name, api_access_group, api_auth_plugin, client_env_var, jwt_key_env_var, jwt_secret_env_var
from scripts.render_goal004_security_controls import render


def test_static_renderer_emits_no_secret_resources():
    assert [doc for doc in render() if doc.get("kind") == "Secret"] == []


def test_runtime_credential_renderer_fails_closed_without_env():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/render_goal004_runtime_credentials.py")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode != 0
    assert "missing" in result.stderr.lower()


def test_runtime_credential_renderer_outputs_expected_secret_metadata_with_env():
    env = os.environ.copy()
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        if api_auth_plugin(api.key) == "jwt":
            env[jwt_key_env_var()] = "runtime-jwt-key-for-tests-12345"
            env[jwt_secret_env_var()] = "runtime-jwt-secret-for-tests-12345"
        else:
            env[client_env_var(client)] = f"runtime-api-key-for-{client}-12345"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/render_goal004_runtime_credentials.py")],
        cwd=ROOT,
        env=env,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
    )
    rendered = [doc for doc in yaml.safe_load_all(result.stdout) if isinstance(doc, dict)]
    assert len(rendered) == 12
    by_name = {doc["metadata"]["name"]: doc for doc in rendered}
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        acl_secret = by_name[acl_secret_name(client, api.key)]
        assert acl_secret["metadata"]["namespace"] == "synthetic-clients"
        assert acl_secret["metadata"]["labels"]["konghq.com/credential"] == "acl"
        assert acl_secret["stringData"]["group"] == api_access_group(api.key)
