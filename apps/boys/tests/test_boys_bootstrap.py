import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

TASKS = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap-tasks.yml").read_text())
INPUT = {
    "boys_pin": "1357",
    "boys_session_key": "preserved-session-key-with-32-characters",
    "boys_cloudflared_token": "existing-tunnel",
}


def encoded(values):
    return {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}


def evaluate(variables):
    loader = DataLoader()
    variables = dict(variables)
    for task in TASKS:
        templar = Templar(loader=loader, variables=variables)
        if "ansible.builtin.set_fact" in task:
            variables.update(templar.template(task["ansible.builtin.set_fact"]))
    return loader, variables


@pytest.mark.parametrize(
    "runtime,tunnel,supplied,available,matches,writes",
    [
        (True, True, {}, True, True, []),
        (True, True, INPUT, True, True, []),
        (False, False, {}, False, True, []),
        (False, False, INPUT, True, True, ["boys-runtime", "boys-cloudflared-token"]),
        (False, True, INPUT, True, True, ["boys-runtime"]),
        (True, False, INPUT, True, True, ["boys-cloudflared-token"]),
        (True, True, {"boys_pin": "2468"}, True, False, []),
        (
            True,
            True,
            {"boys_session_key": "different-session-key-with-32-characters"},
            True,
            False,
            [],
        ),
        (True, True, {"boys_cloudflared_token": "different-tunnel"}, True, False, []),
        (True, True, {"boys_pin": 1357}, False, True, []),
        (True, True, {"boys_session_key": None}, False, False, []),
        (False, False, {**INPUT, "boys_session_key": "short"}, False, True, []),
    ],
)
def test_bootstrap_preserves_access_and_only_creates_missing_secrets(
    runtime, tunnel, supplied, available, matches, writes
):
    variables = {
        "boys_existing_runtime": {
            "resources": [
                {
                    "data": encoded(
                        {"pin": INPUT["boys_pin"], "session-key": INPUT["boys_session_key"]}
                    )
                }
            ]
            if runtime
            else []
        },
        "boys_existing_tunnel": {
            "resources": [{"data": encoded({"token": INPUT["boys_cloudflared_token"]})}]
            if tunnel
            else []
        },
        **supplied,
    }
    loader, variables = evaluate(variables)
    assert variables["boys_bootstrap_available"] is available
    assert variables["boys_bootstrap_matches"] is matches
    templar = Templar(loader=loader, variables=variables)
    actual = []
    for task in TASKS:
        if "ansible.builtin.assert" in task:
            condition = Conditional(loader=loader)
            condition.when = [task["ansible.builtin.assert"]["that"]]
            if not condition.evaluate_conditional(templar, variables):
                break
        if "ansible.builtin.command" not in task:
            continue
        condition = Conditional(loader=loader)
        condition.when = [task["when"]]
        if not condition.evaluate_conditional(templar, variables):
            continue
        command = task["ansible.builtin.command"]
        assert command["argv"][-3:] == ["create", "-f", "-"]
        assert task["no_log"] is True
        secret = yaml.safe_load(templar.template(command["stdin"]))
        assert secret["metadata"]["namespace"] == "boys"
        assert secret["kind"] == "Secret"
        actual.append(secret["metadata"]["name"])
    assert actual == writes


def test_secret_reads_and_value_processing_suppress_output():
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
