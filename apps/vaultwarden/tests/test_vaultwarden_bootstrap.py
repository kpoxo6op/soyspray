import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

TASKS = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap-tasks.yml").read_text())
INPUT = {
    "vaultwarden_agent_email": "automation@vault.soyspray.vip",
    "vaultwarden_agent_master_password": "synthetic-agent-password",
}


def allowed(expression, variables):
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = [expression]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


@pytest.mark.parametrize(
    "exists,supplied,available,matches",
    [
        (True, {}, True, True),
        (True, INPUT, True, True),
        (False, INPUT, True, True),
        (False, {}, False, True),
        (True, {"vaultwarden_agent_master_password": "different"}, True, False),
        (True, {"vaultwarden_agent_email": "human@example.test"}, False, False),
        (False, {**INPUT, "vaultwarden_agent_email": "human@example.test"}, False, True),
        (False, {**INPUT, "vaultwarden_agent_master_password": ""}, False, True),
        (True, {"vaultwarden_agent_master_password": None}, False, False),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_agent_bootstrap_preserves_existing_credentials_and_only_restores_missing_ones(
    exists, supplied, available, matches, check_mode
):
    data = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in {
            "email": INPUT["vaultwarden_agent_email"],
            "master-password": INPUT["vaultwarden_agent_master_password"],
        }.items()
    }
    variables = {
        "vaultwarden_existing_agent": {"resources": [{"data": data}] if exists else []},
        "ansible_check_mode": check_mode,
        "kubeconfig_path": "/test",
        **supplied,
    }
    writes = []
    for task in TASKS:
        templar = Templar(loader=DataLoader(), variables=variables)
        if "ansible.builtin.set_fact" in task:
            variables.update(templar.template(task["ansible.builtin.set_fact"]))
        if "ansible.builtin.assert" in task and not allowed(
            task["ansible.builtin.assert"]["that"], variables
        ):
            break
        if "ansible.builtin.command" in task and allowed(task["when"], variables):
            definition = yaml.safe_load(templar.template(task["ansible.builtin.command"]["stdin"]))
            assert task["no_log"] is True
            assert task["ansible.builtin.command"]["argv"][-3:] == ["create", "-f", "-"]
            assert definition["stringData"] == {
                "email": INPUT["vaultwarden_agent_email"],
                "master-password": INPUT["vaultwarden_agent_master_password"],
            }
            writes.append(definition["metadata"]["name"])
    assert variables["vaultwarden_bootstrap_available"] is available
    assert variables["vaultwarden_bootstrap_matches"] is matches
    assert writes == (
        ["vaultwarden-agent-login"]
        if available and matches and not exists and not check_mode
        else []
    )
