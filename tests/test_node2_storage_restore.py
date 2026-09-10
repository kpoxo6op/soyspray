from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[1] / "playbooks/operations/storage"
TASKS = yaml.safe_load((ROOT / "restore-node2-replicas.yml").read_text())[0]["tasks"]


def passes(name, variables):
    task = next(t for t in TASKS if t["name"] == name)
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = task["ansible.builtin.assert"]["that"]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


def state(mode="post-rejoin"):
    return {
        "node2_restore_mode": mode,
        "recovery_target_ip": "192.168.20.12",
        "node2_evacuation_plan": {
            "kubernetes_node_uid": "old-kube",
            "longhorn_node_uid": "old-longhorn",
            "disk": "original-disk",
        },
        "node2_rejoined_node": {
            "resources": [
                {
                    "metadata": {"uid": "new-kube"},
                    "status": {
                        "addresses": [{"type": "InternalIP", "address": "192.168.20.12"}],
                        "conditions": [{"type": "Ready", "status": "True"}],
                    },
                }
            ]
        },
        "node2_rejoined_longhorn": {
            "resources": [
                {
                    "metadata": {"uid": "new-longhorn"},
                    "status": {
                        "diskStatus": {
                            "new-disk-key": {
                                "diskUUID": "retained-disk-uuid",
                                "conditions": [{"type": "Ready", "status": "True"}],
                            }
                        }
                    },
                }
            ]
        },
        "node2_restore_filesystem": {"stdout": "49c092f4-dd55-41f5-99c6-854f8b44af4e ext4"},
        "node2_restore_disks": [{"key": "new-disk-key"}],
        "node2_restore_disk_key": "new-disk-key",
        "node2_restore_disk_identity": {
            "diskName": "original-disk",
            "diskUUID": "retained-disk-uuid",
        },
    }


def test_recreated_node_requires_rejoin_mode_and_original_rollback_identity():
    name = "Require the expected Kubernetes member and Longhorn node"
    variables = state()
    assert passes(name, variables)
    variables["node2_restore_mode"] = "pre-removal-rollback"
    assert not passes(name, variables)
    variables["node2_rejoined_node"]["resources"][0]["metadata"]["uid"] = "old-kube"
    assert not passes(name, variables)
    variables["node2_rejoined_longhorn"]["resources"][0]["metadata"]["uid"] = "old-longhorn"
    assert passes(name, variables)


@pytest.mark.parametrize(
    "changed", ["none", "filesystem", "disk_name", "disk_uuid", "duplicate_mount"]
)
def test_recreated_disk_is_bound_to_retained_storage(changed):
    variables = state()
    if changed == "filesystem":
        variables["node2_restore_filesystem"]["stdout"] = "different-uuid ext4"
    elif changed == "disk_name":
        variables["node2_restore_disk_identity"]["diskName"] = "other-disk"
    elif changed == "disk_uuid":
        variables["node2_restore_disk_identity"]["diskUUID"] = "other-uuid"
    elif changed == "duplicate_mount":
        variables["node2_restore_disks"].append({"key": "ambiguous-disk"})
    accepted = passes("Require the original filesystem and on-disk identity", variables) and passes(
        "Match the live Longhorn entry to the retained disk", variables
    )
    assert accepted is (changed == "none")


def test_rebuild_waits_for_all_read_write_copies():
    tasks = yaml.safe_load((ROOT / "restore-node2-volume.yml").read_text())
    task = next(t for t in tasks if t["name"] == "Wait for synchronized read-write engine copies")
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = task["until"]
    for last_mode, expected in (("WO", False), ("ERR", False), ("RW", True)):
        variables = {
            "node2_volume_entry": {"restore_replicas": 3},
            "node2_engines_after_restore": {
                "resources": [
                    {
                        "status": {
                            "replicaModeMap": {"first": "RW", "second": "RW", "new": last_mode}
                        }
                    }
                ]
            },
        }
        assert (
            condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
            is expected
        )
