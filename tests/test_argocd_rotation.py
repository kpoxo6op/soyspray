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


@pytest.mark.parametrize("action", ["remove", "restore"])
def test_stale_authentik_fields_have_atomic_field_scoped_rollback(action):
    # Deleting/replacing the entire shared Secret would break unrelated logins.
    # The Argo rotation contract does not own Authentik's separate Secret.
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/security/retire-authentik-argo-keys.yml").read_text()
    )[0]
    fields = play["vars"]["authentik_argo_fields"]
    source = {
        "metadata": {"uid": "reviewed", "resourceVersion": "reviewed-version"},
        "data": {"SSO_PASSWORD": "unchanged", "ARGOCD_OIDC_CLIENT_SECRET": "unchanged"},
    }
    original = copy.deepcopy(source)
    original["data"].update({field: "original-private-value" for field in fields})
    if action == "remove":
        source = copy.deepcopy(original)
    variables = {
        "authentik_runtime_uid": "reviewed",
        "authentik_runtime_version": "reviewed-version",
        "original_runtime": original,
        "runtime_patch": [],
    }
    env = NativeEnvironment()
    for task in play["tasks"]:
        fact = task.get("ansible.builtin.set_fact", {}).get("runtime_patch")
        if fact is None:
            continue
        if isinstance(fact, list):
            variables["runtime_patch"] = [
                {k: env.from_string(v).render(variables) for k, v in op.items()} for op in fact
            ]
        elif task["when"] == f"authentik_argo_action == '{action}'":
            for field in fields:
                variables["item"] = field
                variables["runtime_patch"] = env.from_string(fact).render(variables)
    result = jsonpatch.apply_patch(source, variables["runtime_patch"])
    assert result["metadata"] == source["metadata"]
    assert {k: v for k, v in result["data"].items() if k not in fields} == {
        k: v for k, v in source["data"].items() if k not in fields
    }
    assert all((field in result["data"]) == (action == "restore") for field in fields)
    for field in ("uid", "resourceVersion"):
        stale = copy.deepcopy(source)
        stale["metadata"][field] = "unexpected"
        with pytest.raises(jsonpatch.JsonPatchTestFailed):
            jsonpatch.apply_patch(stale, variables["runtime_patch"])
        assert stale["data"] == source["data"]
