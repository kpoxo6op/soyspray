from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("app,uid", [("boys", 1000), ("vaultwarden", 0), ("obsidian", 0)])
def test_restore_inspector_uses_numeric_application_identity(app, uid):
    play = yaml.safe_load((ROOT / "playbooks/operations/recovery/restore-volume.yml").read_text())[
        0
    ]
    pod = next(
        definition
        for task in play["tasks"]
        if isinstance(definition := task.get("kubernetes.core.k8s", {}).get("definition"), dict)
        and definition.get("kind") == "Pod"
    )
    rendered = Templar(
        loader=DataLoader(),
        variables={
            **play["vars"],
            "recovery_app": app,
            "recovery_check_id": "test",
        },
    ).template(pod)
    identity = rendered["spec"]["securityContext"]
    assert type(identity["runAsUser"]) is int
    assert type(identity["runAsGroup"]) is int
    assert identity["runAsUser"] == identity["runAsGroup"] == uid
