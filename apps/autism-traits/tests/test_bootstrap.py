from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

PLAY = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap.yml").read_text())[0]


@pytest.mark.parametrize(
    "token,resources,available,writes",
    [
        ("", [{"data": {"token": "existing"}}], True, False),
        ("", [], False, False),
        ("", [{"data": {}}], False, False),
        ("supplied-runtime-input", [], True, True),
        (None, [{"data": {"token": "existing"}}], False, False),
    ],
)
def test_bootstrap_preserves_existing_identity_unless_an_input_is_supplied(
    token, resources, available, writes
):
    loader = DataLoader()
    variables = {
        "autism_traits_existing_token": {"resources": resources},
        "autism_traits_cloudflared_token": token,
    }
    templar = Templar(loader=loader, variables=variables)
    fact = next(
        t["ansible.builtin.set_fact"] for t in PLAY["tasks"] if "ansible.builtin.set_fact" in t
    )
    assert templar.template(fact["autism_traits_identity_available"]) is available
    if not available:
        return  # The assertion stops the play before any write task.
    for task in PLAY["tasks"]:
        if "kubernetes.core.k8s" not in task:
            continue
        condition = Conditional(loader=loader)
        condition.when = [task["when"]]
        assert condition.evaluate_conditional(templar, variables) is writes
    secret = next(
        t
        for t in PLAY["tasks"]
        if isinstance(t.get("kubernetes.core.k8s", {}).get("definition"), dict)
        and t["kubernetes.core.k8s"]["definition"].get("kind") == "Secret"
    )
    assert secret["no_log"] is True
    assert secret["kubernetes.core.k8s"]["definition"]["metadata"] == {
        "name": "autism-traits-cloudflared-token",
        "namespace": "autism-traits",
    }
