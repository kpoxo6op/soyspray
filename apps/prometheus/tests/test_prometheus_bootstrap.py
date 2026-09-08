import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

TASKS = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap-tasks.yml").read_text())
TOKEN = "synthetic-telegram-token"


def allowed(expression, variables):
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = expression if isinstance(expression, list) else [expression]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


@pytest.mark.parametrize("existing", [True, False])
@pytest.mark.parametrize("namespace", [True, False])
@pytest.mark.parametrize("check_mode", [True, False])
@pytest.mark.parametrize("supplied", ["missing", TOKEN, "different", "", " ", None, 123, {}])
def test_bootstrap_preserves_identity_and_creates_only_a_missing_secret(
    existing, namespace, check_mode, supplied
):
    variables = {
        "kubeconfig_path": "/test",
        "ansible_check_mode": check_mode,
        "prometheus_namespace": {"resources": [{}] if namespace else []},
        "prometheus_existing_telegram": {
            "resources": [
                {
                    "data": {
                        "PROMETHEUS_TELEGRAM_BOT_TOKEN": base64.b64encode(TOKEN.encode()).decode()
                    }
                }
            ]
            if existing
            else []
        },
    }
    if supplied != "missing":
        variables["prometheus_telegram_bot_token"] = supplied
    writes = []
    passed = True
    for task in TASKS:
        templar = Templar(loader=DataLoader(), variables=variables)
        if "ansible.builtin.set_fact" in task:
            assert task["no_log"] is True
            variables.update(templar.template(task["ansible.builtin.set_fact"]))
        if "ansible.builtin.assert" in task and not allowed(
            task["ansible.builtin.assert"]["that"], variables
        ):
            passed = False
            break
        if "ansible.builtin.command" in task and allowed(task["when"], variables):
            command = templar.template(task["ansible.builtin.command"])
            assert task["no_log"] is True
            assert command["argv"] == ["kubectl", "--kubeconfig", "/test", "create", "-f", "-"]
            value = command["stdin"]
            writes.append(yaml.safe_load(value) if isinstance(value, str) else value)
        assert "kubernetes.core.k8s" not in task
    selected = (TOKEN if existing else "") if supplied == "missing" else supplied
    valid = isinstance(selected, str) and bool(selected.strip())
    expected = namespace and valid and (not existing or selected == TOKEN)
    assert passed == expected
    assert writes == (
        [
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": "alertmanager-telegram-secret",
                    "namespace": "monitoring",
                },
                "type": "Opaque",
                "stringData": {"PROMETHEUS_TELEGRAM_BOT_TOKEN": selected},
            }
        ]
        if expected and not existing and not check_mode
        else []
    )


def test_secret_reads_and_value_processing_suppress_output():
    for task in TASKS:
        if (
            any(
                key in task
                for key in (
                    "kubernetes.core.k8s_info",
                    "ansible.builtin.set_fact",
                    "ansible.builtin.command",
                )
            )
            and task.get("register") != "prometheus_namespace"
        ):
            assert task["no_log"] is True
