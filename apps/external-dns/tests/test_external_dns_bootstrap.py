import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

PLAY = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap.yml").read_text())[0]
EXISTING = [{"data": {"api-token": base64.b64encode(b"existing-token").decode()}}]


@pytest.mark.parametrize(
    "token,resources,check_mode,allowed,writes",
    [
        ("", EXISTING, False, True, []),
        ("existing-token", EXISTING, False, True, []),
        ("different-token", EXISTING, False, False, []),
        ("", [], False, False, []),
        ("", [{"data": {}}], False, False, []),
        ("supplied-input", [{"data": {}}], False, False, []),
        ("supplied-input", [], False, True, ["namespace", "secret"]),
        ("supplied-input", [], True, True, ["namespace"]),
        (None, EXISTING, False, False, []),
        (12345, [], False, False, []),
    ],
)
def test_bootstrap_never_replaces_an_existing_provider_identity(
    token, resources, check_mode, allowed, writes
):
    loader = DataLoader()
    variables = {
        "external_dns_existing_token": {"resources": resources},
        "external_dns_cloudflare_api_token": token,
        "ansible_check_mode": check_mode,
        "kubeconfig_path": "/private/kubeconfig",
    }
    actual = []
    passed = True
    for task in PLAY["tasks"]:
        templar = Templar(loader=loader, variables=variables)
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
            actual.append("namespace")
        if "ansible.builtin.command" in task:
            command = task["ansible.builtin.command"]
            assert command["argv"][-3:] == ["create", "-f", "-"]
            assert task["no_log"] is True
            definition = yaml.safe_load(templar.template(command["stdin"]))
            assert definition["metadata"] == {
                "name": "cloudflare-api-token",
                "namespace": "external-dns",
            }
            assert definition["stringData"]["api-token"] == token
            actual.append("secret")
    assert passed is allowed
    assert actual == writes


def test_sensitive_reads_and_processing_suppress_output():
    for task in PLAY["tasks"]:
        if any(
            key in task
            for key in (
                "kubernetes.core.k8s_info",
                "ansible.builtin.set_fact",
                "ansible.builtin.command",
            )
        ):
            assert task["no_log"] is True
