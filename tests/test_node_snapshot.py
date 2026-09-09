from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "playbooks/operations/nodes/snapshot-etcd.yml"


def task_by_name(tasks: list[dict], name: str) -> dict:
    return next(task for task in tasks if task["name"] == name)


def test_etcd_snapshot_is_fixed_to_a_survivor_and_fetched_off_node() -> None:
    play = yaml.safe_load(SNAPSHOT.read_text())[0]
    tasks = play["tasks"]

    assert play["hosts"] == "node-0"
    guard = task_by_name(tasks, "Require the designated survivor and an explicit snapshot label")[
        "ansible.builtin.assert"
    ]["that"]
    assert "inventory_hostname == 'node-0'" in guard
    assert any("etcd_snapshot_label" in condition for condition in guard)

    save = task_by_name(tasks, "Save the native etcd snapshot")["ansible.builtin.command"]["argv"]
    assert save[:3] == ["{{ etcdctl_bin }}", "snapshot", "save"]

    validate = task_by_name(tasks, "Validate the native snapshot")["ansible.builtin.command"][
        "argv"
    ]
    assert validate[:3] == ["{{ etcdutl_bin }}", "snapshot", "status"]

    transfer = task_by_name(tasks, "Fetch the validated snapshot through a private staging copy")
    fetch = task_by_name(transfer["block"], "Fetch the staged files without privileged encoding")
    assert fetch["ansible.builtin.fetch"]["flat"] is True
    assert fetch["become"] is False
    assert "{{ etcd_snapshot_path }}" in fetch["loop"]
    cleanup = task_by_name(transfer["always"], "Remove the private transfer directory")
    assert cleanup["ansible.builtin.file"]["state"] == "absent"
