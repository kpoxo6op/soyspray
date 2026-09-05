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
        / "playbooks/argocd/applications/media/media-helper/media-helper-application.yaml"
    ).read_text()
)["spec"]


@pytest.mark.parametrize(
    "change",
    [
        "legacy",
        "native",
        "wrong-source",
        "active-operation",
        "deleting",
    ],
)
def test_adoption_requires_known_idle_app_and_preserves_foreign_finalizers(change):
    app = {
        "spec": copy.deepcopy(LEGACY),
        "metadata": {
            "resourceVersion": "123",
            "finalizers": ["unrelated.example/keep", "resources-finalizer.argocd.argoproj.io"],
        },
        "status": {},
    }
    if change == "native":
        app["spec"] = copy.deepcopy(SPEC)
    elif change == "wrong-source":
        app["spec"]["source"]["targetRevision"] = "unexpected"
    elif change == "active-operation":
        app["status"]["operationState"] = {"phase": "Running"}
    elif change == "deleting":
        app["metadata"]["deletionTimestamp"] = "2026-09-06T00:00:00Z"
    variables = {
        **PLAY["vars"],
        "media_helper_existing_app": {"resources": [app]},
        "media_helper_legacy_spec": LEGACY,
        "media_helper_native_spec": SPEC,
    }
    allowed = True
    for task in PLAY["tasks"]:
        if "ansible.builtin.assert" not in task:
            continue
        loader = DataLoader()
        condition = Conditional(loader=loader)
        condition.when = task["ansible.builtin.assert"]["that"]
        if not condition.evaluate_conditional(
            Templar(loader=loader, variables=variables), variables
        ):
            allowed = False
            break
    assert allowed == (change in ["legacy", "native"])
    if allowed:
        task = PLAY["tasks"][-1]
        templar = Templar(loader=DataLoader(), variables=variables)
        variables.update(templar.template(task["vars"]))
        patch = Templar(loader=DataLoader(), variables=variables).template(
            task["kubernetes.core.k8s_json_patch"]["patch"]
        )
        assert patch == [
            {"op": "test", "path": "/metadata/resourceVersion", "value": "123"},
            {"op": "replace", "path": "/metadata/finalizers", "value": ["unrelated.example/keep"]},
        ]
