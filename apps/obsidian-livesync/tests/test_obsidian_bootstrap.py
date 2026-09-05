import base64
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

TASKS = yaml.safe_load((Path(__file__).resolve().parents[1] / "bootstrap-tasks.yml").read_text())
VALUES = {
    "couchdb": {
        "adminUsername": "operator",
        "adminPassword": "synthetic-password",
        "cookieAuthSecret": "synthetic-cookie",
        "erlangCookie": "synthetic-erlang",
    },
    "offsite": {
        "AWS_ACCESS_KEY_ID": "synthetic-key",
        "AWS_SECRET_ACCESS_KEY": "synthetic-secret",
        "AWS_REGION": "ap-southeast-2",
        "BUCKET_NAME": "existing-bucket",
        "BACKUP_PREFIX": "existing/",
    },
}


def allowed(expression, variables):
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = expression if isinstance(expression, list) else [expression]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


@pytest.mark.parametrize("missing", [[], ["couchdb"], ["offsite"], ["couchdb", "offsite"]])
@pytest.mark.parametrize(
    "change", ["matching", "unsupplied", "different", "empty", "null", "extra-key", "not-a-map"]
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_bootstrap_checks_both_identities_before_restoring_only_missing_secrets(
    missing, change, check_mode
):
    import copy

    supplied = {
        "obsidian_" + part + "_identity": copy.deepcopy(value) for part, value in VALUES.items()
    }
    if change == "unsupplied":
        supplied = {}
    elif change == "different":
        supplied["obsidian_offsite_identity"]["BUCKET_NAME"] = "another-bucket"
    elif change == "empty":
        supplied["obsidian_couchdb_identity"]["adminPassword"] = " "
    elif change == "null":
        supplied["obsidian_couchdb_identity"]["adminPassword"] = None
    elif change == "extra-key":
        supplied["obsidian_couchdb_identity"]["unrelated"] = "extra"
    elif change == "not-a-map":
        supplied["obsidian_couchdb_identity"] = "invalid"
    variables = {"ansible_check_mode": check_mode, "kubeconfig_path": "/test", **supplied}
    for part, values in VALUES.items():
        data = {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}
        variables["obsidian_existing_" + part] = {
            "resources": [] if part in missing else [{"data": data}]
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
            definition = templar.template(task["ansible.builtin.command"]["stdin"])
            if isinstance(definition, str):
                definition = yaml.safe_load(definition)
            assert task["no_log"] is True
            assert task["ansible.builtin.command"]["argv"][-3:] == ["create", "-f", "-"]
            part = (
                "couchdb"
                if definition["metadata"]["name"] == "obsidian-livesync-couchdb"
                else "offsite"
            )
            assert definition["metadata"]["namespace"] == "obsidian"
            assert definition["stringData"] == variables["obsidian_bootstrap_" + part]
            writes.append(part)
    available = change in ["matching", "different"] or (change == "unsupplied" and not missing)
    matches = change != "different" or "offsite" in missing
    assert variables["obsidian_bootstrap_available"] is available
    assert writes == (missing if available and matches and not check_mode else [])
