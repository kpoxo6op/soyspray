import copy
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

APP = Path(__file__).resolve().parents[1]
PLAY = yaml.safe_load((APP / "adopt.yml").read_text())[0]
SPEC = yaml.safe_load((APP / "argocd/application.yaml").read_text())["spec"]
LEGACY = yaml.safe_load(
    (
        APP.parents[1]
        / "playbooks/argocd/applications/security/vaultwarden/vaultwarden-application.yaml"
    ).read_text()
)["spec"]


@pytest.mark.parametrize(
    "change,allowed",
    [
        (lambda obj: None, True),
        (
            lambda obj: obj.update(spec=copy.deepcopy(LEGACY)),
            True,
        ),
        (lambda obj: obj["spec"]["source"].update(targetRevision="another-preview"), False),
        (lambda obj: obj["spec"]["destination"].update(namespace="another-app"), False),
        (lambda obj: obj["spec"].update(project="foreign"), False),
        (lambda obj: obj["metadata"].update(deletionTimestamp="2026-01-01T00:00:00Z"), False),
        (lambda obj: obj["status"].update(operationState={"phase": "Running"}), False),
    ],
)
def test_adoption_requires_known_ownership_and_an_idle_live_application(change, allowed):
    obj = {
        "spec": copy.deepcopy(SPEC),
        "metadata": {
            "resourceVersion": "123",
            "finalizers": [
                "resources-finalizer.argocd.argoproj.io",
                "other-controller.example/keep",
            ],
        },
        "status": {},
    }
    change(obj)
    loader = DataLoader()
    variables = {
        "playbook_dir": str(APP),
        "vaultwarden_existing_app": {"resources": [obj]},
        **PLAY["vars"],
    }
    assertion = PLAY["tasks"][1]
    templar = Templar(loader=loader, variables=variables)
    variables.update(templar.template(assertion["vars"]))
    templar = Templar(loader=loader, variables=variables)
    condition = Conditional(loader=loader)
    condition.when = assertion["ansible.builtin.assert"]["that"]
    assert condition.evaluate_conditional(templar, variables) is allowed
    patch_task = PLAY["tasks"][2]
    variables.update(templar.template(patch_task["vars"]))
    patch = Templar(loader=loader, variables=variables).template(
        patch_task["kubernetes.core.k8s_json_patch"]["patch"]
    )
    assert patch == [
        {"op": "test", "path": "/metadata/resourceVersion", "value": "123"},
        {
            "op": "replace",
            "path": "/metadata/finalizers",
            "value": ["other-controller.example/keep"],
        },
    ]
