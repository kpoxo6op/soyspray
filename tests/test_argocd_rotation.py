"""Guard the credential mutation boundary independently of native inventory."""

import base64
import copy
from pathlib import Path

import jsonpatch
import pytest
import yaml
from jinja2.nativetypes import NativeEnvironment

ROOT = Path(__file__).resolve().parents[1]


def test_rotation_patch_refuses_stale_objects_and_preserves_other_keys():
    # A broader patch could replace signing/SSO material or race an operator.
    # Login and inventory tests do not inspect the live mutation boundary.
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/security/rotate-argocd-admin.yml").read_text()
    )[0]
    block = next(task["block"] for task in play["tasks"] if "rescue" in task)
    patch = block[0]["kubernetes.core.k8s_json_patch"]["patch"]
    env = NativeEnvironment()
    env.filters["b64encode"] = lambda value: base64.b64encode(value.encode()).decode()
    variables = {
        "argocd_secret_uid": "reviewed-uid",
        "argocd_secret_version": "reviewed-version",
        "argocd_admin": {"password_hash": "dummy-private-hash", "password_mtime": "dummy-UTC"},
    }
    rendered = [
        {key: env.from_string(value).render(variables) for key, value in operation.items()}
        for operation in patch
    ]
    source = {
        "metadata": {"uid": "reviewed-uid", "resourceVersion": "reviewed-version"},
        "data": {
            "admin.password": "previous-hash",
            "admin.passwordMtime": "previous-cutoff",
            "server.secretkey": "dummy-signing-key",
            "oidc.authentik.clientSecret": "dummy-oidc-key",
            "tls.crt": "dummy-cert",
            "tls.key": "dummy-tls-key",
        },
    }
    result = jsonpatch.apply_patch(source, rendered)
    fields = {"admin.password", "admin.passwordMtime"}
    assert {key for key in source["data"] if result["data"][key] != source["data"][key]} == fields
    assert result["metadata"] == source["metadata"]
    for field in ("uid", "resourceVersion"):
        stale = copy.deepcopy(source)
        stale["metadata"][field] = "unexpected"
        with pytest.raises(jsonpatch.JsonPatchTestFailed):
            jsonpatch.apply_patch(stale, rendered)
        assert stale["data"] == source["data"]
