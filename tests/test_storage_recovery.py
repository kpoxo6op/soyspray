from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "playbooks/operations/storage/prepare-existing-longhorn-storage.yml"


def task_by_name(tasks: list[dict], name: str) -> dict:
    return next(task for task in tasks if task["name"] == name)


def test_retained_storage_operation_cannot_format_or_repartition() -> None:
    text = STORAGE.read_text()
    play = yaml.safe_load(text)[0]

    assert play["hosts"] == "node-2"
    assert play["vars"]["longhorn_storage_uuid"] == ("49c092f4-dd55-41f5-99c6-854f8b44af4e")
    assert play["vars"]["longhorn_storage_model"] == "PNY 500GB SATA S"
    for destructive_word in ("wipefs", "mkfs", "parted", "filesystem:"):
        assert destructive_word not in text

    guard = task_by_name(play["pre_tasks"], "Require the retained node-2 target")
    conditions = guard["ansible.builtin.assert"]["that"]
    assert "inventory_hostname == 'node-2'" in conditions
    assert "ansible_host == '192.168.20.12'" in conditions

    fstab = task_by_name(play["tasks"], "Keep the retained filesystem in fstab by UUID")
    assert "UUID={{ longhorn_storage_uuid }}" in fstab["ansible.builtin.lineinfile"]["line"]
