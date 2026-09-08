import json

from scripts.check_durable_data import HOME_ASSISTANT_REGISTRIES, check


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
