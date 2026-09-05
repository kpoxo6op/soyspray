import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

TASKS = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap-tasks.yml").read_text())
INPUT = {
    "domain_health_healthchecks_ping_url": "https://hc.example/test-id",
    "domain_health_expected_nameservers": "ada.ns.example,bob.ns.example",
    "domain_health_cloudflare_api_token": "provider-token",
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
    "config,provider,supplied,available,matches,writes",
    [
        (True, True, {}, True, True, []),
        (True, True, INPUT, True, True, []),
        (False, False, {}, False, True, []),
        (False, False, INPUT, True, True, ["domain-health-config", "cloudflare-api-token"]),
        (False, True, INPUT, True, True, ["domain-health-config"]),
        (True, False, INPUT, True, True, ["cloudflare-api-token"]),
        (
            True,
            True,
            {"domain_health_healthchecks_ping_url": "https://hc.example/different"},
            True,
            False,
            [],
        ),
        (
            True,
            True,
            {"domain_health_expected_nameservers": "other.ns.example"},
            True,
            False,
            [],
        ),
        (True, True, {"domain_health_cloudflare_api_token": "different-provider"}, True, False, []),
        (True, True, {"domain_health_healthchecks_ping_url": 1357}, False, False, []),
        (True, True, {"domain_health_expected_nameservers": None}, False, False, []),
        (False, False, {**INPUT, "domain_health_expected_nameservers": ""}, False, True, []),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_bootstrap_preserves_access_and_only_creates_missing_secrets(
    config, provider, supplied, available, matches, writes, check_mode
):
    variables = {
        "ansible_check_mode": check_mode,
        "domain_health_existing_config": {
            "resources": [
                {
                    "data": encoded(
                        {
                            "healthchecks-ping-url": INPUT["domain_health_healthchecks_ping_url"],
                            "expected-nameservers": INPUT["domain_health_expected_nameservers"],
                        }
                    )
                }
            ]
            if config
            else []
        },
        "domain_health_existing_provider": {
            "resources": [
                {"data": encoded({"api-token": INPUT["domain_health_cloudflare_api_token"]})}
            ]
            if provider
            else []
        },
        **supplied,
    }
    loader, variables = evaluate(variables)
    assert variables["domain_health_bootstrap_available"] is available
    assert variables["domain_health_bootstrap_matches"] is matches
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
        assert secret["metadata"]["namespace"] == "domain-health"
        assert secret["kind"] == "Secret"
        actual.append(secret["metadata"]["name"])
    assert actual == ([] if check_mode else writes)


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
