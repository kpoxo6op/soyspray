from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "playbooks/operations/storage"


def task_by_name(tasks: list[dict], name: str) -> dict:
    return next(task for task in tasks if task.get("name") == name)


def test_node2_evacuation_is_identity_bound_and_uses_native_eviction() -> None:
    play = yaml.safe_load((STORAGE / "evacuate-node2.yml").read_text())[0]
    assert play["hosts"] == "kube_control_plane[0]"
    assert play["vars"]["removal_target"] == "node-2"
    assert play["vars"]["removal_target_ip"] == "192.168.20.12"
    assert play["vars"]["removal_target_disk"] == "default-disk-60b0ac7c10410705"
    assert play["vars"]["node2_restore_replica_overrides"] == {
        "pvc-c43a407a-b315-458d-b6ab-a73aa882c0fb": 1
    }

    disable = task_by_name(play["tasks"], "Disable new scheduling on the target node and disk")[
        "kubernetes.core.k8s_json_patch"
    ]["patch"]
    assert {item["path"] for item in disable} == {
        "/metadata/uid",
        "/spec",
        "/spec/allowScheduling",
        "/spec/disks/{{ removal_target_disk }}/allowScheduling",
    }
    request = task_by_name(play["tasks"], "Request native eviction from the target node and disk")[
        "kubernetes.core.k8s_json_patch"
    ]["patch"]
    assert request[-2:] == [
        {"op": "replace", "path": "/spec/evictionRequested", "value": True},
        {
            "op": "replace",
            "path": "/spec/disks/{{ removal_target_disk }}/evictionRequested",
            "value": True,
        },
    ]

    text = (STORAGE / "evacuate-node2.yml").read_text()
    assert "state: absent" not in text
    assert "kind: Replica\n" in text
    assert "disable-eviction" not in text
    assert "node2_evacuation_evidence.stat.exists" in text
    assert "Reuse the immutable restoration plan" in text
    assert "evacuate-node2-volume.yml" in text


def test_node2_replica_policies_are_restored_from_private_evidence() -> None:
    play = yaml.safe_load((STORAGE / "restore-node2-replicas.yml").read_text())[0]
    tasks = play["tasks"]
    assert play["vars"]["recovery_target"] == "node-2"
    assert play["vars"]["recovery_target_ip"] == "192.168.20.12"
    assert task_by_name(tasks, "Load the immutable evacuation plan")["ansible.builtin.set_fact"][
        "node2_evacuation_plan"
    ].startswith("{{ lookup('file'")

    helper = (STORAGE / "restore-node2-volume.yml").read_text()
    assert "/spec/numberOfReplicas" in helper
    assert "node2_volume_entry.restore_replicas" in helper
    assert "status.robustness == 'healthy'" in helper
    assert "state: absent" not in helper
    assert "in [2, node2_volume_entry.restore_replicas | int]" in helper
    assert "node2_restore_mode" in (STORAGE / "restore-node2-replicas.yml").read_text()
