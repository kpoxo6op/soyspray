import json
from pathlib import Path

import yaml

from scripts.check_durable_data import HOME_ASSISTANT_REGISTRIES, check

ROOT = Path(__file__).resolve().parents[1]


def test_home_assistant_restore_checks_private_registries(tmp_path):
    storage = tmp_path / ".storage"
    storage.mkdir()
    for name, collection in HOME_ASSISTANT_REGISTRIES.items():
        value = [{}] if collection != "exposed_entities" else {"light.peanut": True}
        (storage / name).write_text(json.dumps({"data": {collection: value}}))

    result = check(tmp_path, "home-assistant-config")

    private = result["home_assistant_private_state"]
    assert set(private) == set(HOME_ASSISTANT_REGISTRIES)
    assert all(value["records"] == 1 for value in private.values())
    assert all(len(value["sha256"]) == 64 for value in private.values())


def test_home_assistant_declares_and_protects_its_durable_claim():
    application = yaml.safe_load((ROOT / "argocd/catalog/home-assistant.yaml").read_text())
    annotations = application["metadata"]["annotations"]
    assert annotations["soyspray.vip/data-claims"] == ("home-automation/home-assistant-config")
    assert "Longhorn durable-small" in annotations["soyspray.vip/backup"]

    claim = yaml.safe_load((ROOT / "apps/home-assistant/manifests/pvc-config.yaml").read_text())
    options = set(claim["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(","))
    assert {"Prune=false", "Delete=false"} <= options

    recovery = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/configure-longhorn.yml").read_text()
    )[0]
    assert {
        "app": "home-assistant",
        "namespace": "home-automation",
        "claim": "home-assistant-config",
        "group": "durable-small",
    } in recovery["vars"]["recovery_claims"]
