import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "apps/bootstrap-secret-tasks.yml").read_text())


@pytest.fixture(
    params=[
        (
            "external-dns",
            "cloudflare-api-token",
            "api-token",
            "external_dns_cloudflare_api_token",
            "namespace.yaml",
        ),
        (
            "autism-traits",
            "autism-traits-cloudflared-token",
            "token",
            "autism_traits_cloudflared_token",
            "manifests/namespace.yaml",
        ),
    ]
)
def identity(request):
    return request.param


def test_app_passes_secret_identity_to_shared_tasks(identity):
    app, name, key, input_name, namespace_file = identity
    play = yaml.safe_load((ROOT / "apps" / app / "bootstrap.yml").read_text())[0]
    task = play["tasks"][0]
    assert task["ansible.builtin.import_tasks"] == "../bootstrap-secret-tasks.yml"
    args = task["vars"]
    assert args["bootstrap_secret_name"] == name
    assert args["bootstrap_secret_namespace"] == app
    assert args["bootstrap_secret_key"] == key
    assert args["bootstrap_secret_input"] == "{{ " + input_name + " | default('') }}"
    assert args["bootstrap_secret_namespace_file"] == "{{ playbook_dir }}/" + namespace_file


@pytest.mark.parametrize(
    "token,existing,check_mode,allowed,writes",
    [
        ("", "valid", False, True, []),
        ("existing-token", "valid", False, True, []),
        ("different-token", "valid", False, False, []),
        ("", None, False, False, []),
        ("", "empty", False, False, []),
        ("supplied-input", "empty", False, False, []),
        ("supplied-input", None, False, True, ["namespace", "secret"]),
        ("supplied-input", None, True, True, ["namespace"]),
        (None, "valid", False, False, []),
        (12345, None, False, False, []),
        ("different-token", "valid", True, False, []),
        ("existing-token", "valid", True, True, []),
        ("  ", None, False, False, []),
    ],
)
def test_shared_bootstrap_tasks_preserve_identity_and_create_only_missing_secret(
    identity, token, existing, check_mode, allowed, writes
):
    app, name, key, _, namespace_file = identity
    resources = (
        []
        if existing is None
        else [
            {
                "data": {key: base64.b64encode(b"existing-token").decode()}
                if existing == "valid"
                else {}
            }
        ]
    )
    loader = DataLoader()
    variables = {
        "bootstrap_secret_existing": {"resources": resources},
        "bootstrap_secret_input": token,
        "bootstrap_secret_name": name,
        "bootstrap_secret_namespace": app,
        "bootstrap_secret_key": key,
        "bootstrap_secret_namespace_file": str(ROOT / "apps" / app / namespace_file),
        "ansible_check_mode": check_mode,
        "kubeconfig_path": "/private/kubeconfig",
    }
    actual = []
    passed = True
    for task in TASKS:
        templar = Templar(loader=loader, variables=variables)
        if "kubernetes.core.k8s_info" in task:
            assert templar.template(task["kubernetes.core.k8s_info"]) == {
                "api_version": "v1",
                "kind": "Secret",
                "namespace": app,
                "name": name,
                "kubeconfig": "/private/kubeconfig",
            }
        if "ansible.builtin.set_fact" in task:
            variables.update(templar.template(task["ansible.builtin.set_fact"]))
        if "ansible.builtin.assert" in task:
            condition = Conditional(loader=loader)
            condition.when = [task["ansible.builtin.assert"]["that"]]
            if not condition.evaluate_conditional(
                Templar(loader=loader, variables=variables), variables
            ):
                passed = False
                break
        if "when" not in task:
            continue
        condition = Conditional(loader=loader)
        condition.when = [task["when"]]
        if not condition.evaluate_conditional(templar, variables):
            continue
        if "kubernetes.core.k8s" in task:
            params = templar.template(task["kubernetes.core.k8s"])
            assert params["state"] == "present"
            assert params["kubeconfig"] == "/private/kubeconfig"
            assert params["definition"]["kind"] == "Namespace"
            assert params["definition"]["metadata"]["name"] == app
            actual.append("namespace")
        if "ansible.builtin.command" in task:
            command = task["ansible.builtin.command"]
            assert command["argv"] == [
                "kubectl",
                "--kubeconfig",
                "{{ kubeconfig_path }}",
                "create",
                "-f",
                "-",
            ]
            assert task["no_log"] is True
            definition = yaml.safe_load(templar.template(command["stdin"]))
            assert definition["metadata"] == {
                "name": name,
                "namespace": app,
            }
            assert definition["stringData"][key] == token
            actual.append("secret")
    assert passed is allowed
    assert actual == writes


def test_shared_bootstrap_tasks_hide_sensitive_operations_and_keep_order():
    modules = [next(key for key in task if "." in key) for task in TASKS]
    assert modules == [
        "kubernetes.core.k8s_info",
        "ansible.builtin.set_fact",
        "ansible.builtin.assert",
        "ansible.builtin.assert",
        "kubernetes.core.k8s",
        "ansible.builtin.command",
    ]
    for task in TASKS:
        if any(
            key in task
            for key in (
                "kubernetes.core.k8s_info",
                "ansible.builtin.set_fact",
                "ansible.builtin.command",
            )
        ):
            assert task["no_log"] is True
