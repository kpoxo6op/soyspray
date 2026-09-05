from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

APP = Path(__file__).resolve().parents[1]
PLAY = yaml.safe_load((APP / "adopt.yml").read_text())[0]
NATIVE = yaml.safe_load((APP / "argocd/application.yaml").read_text())["spec"]


@pytest.mark.parametrize(
    "change,accepted",
    [
        ({}, True),
        ({"source": {**NATIVE["source"], "targetRevision": "unreviewed"}}, False),
        ({"source": {**NATIVE["source"], "path": "another-app"}}, False),
        ({"project": "default"}, False),
        ({"destination": {**NATIVE["destination"], "namespace": "another-app"}}, False),
        ({"destination": {**NATIVE["destination"], "server": "https://elsewhere"}}, False),
        ({"deleting": True}, False),
        ({"phase": "Running"}, False),
        ({"phase": "Terminating"}, False),
    ],
)
def test_adoption_rejects_changed_ownership_and_active_operations(change, accepted):
    spec = {**deepcopy(NATIVE), **{k: v for k, v in change.items() if k in NATIVE}}
    metadata = {"uid": "existing"}
    if change.get("deleting"):
        metadata["deletionTimestamp"] = "2026-09-05T00:00:00Z"
    variables = {
        "boys_adopt_source": spec["source"],
        "boys_native_source": NATIVE["source"],
        "boys_legacy_source": {**NATIVE["source"], "kustomize": {"patches": []}},
        "boys_adopt_application": {
            "resources": [
                {
                    "metadata": metadata,
                    "spec": spec,
                    "status": {"operationState": {"phase": change.get("phase", "Succeeded")}},
                }
            ]
        },
    }
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = next(
        t["ansible.builtin.assert"]["that"]
        for t in PLAY["tasks"]
        if "ansible.builtin.assert" in t
        and "boys_adopt_source in [boys_legacy_source, boys_native_source]"
        in t["ansible.builtin.assert"]["that"]
    )
    assert (
        condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
        == accepted
    )
