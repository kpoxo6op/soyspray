from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "playbooks/operations/storage/protect-loki-before-node2.yml"


def task_by_name(tasks: list[dict], name: str) -> dict:
    return next(task for task in tasks if task["name"] == name)


def test_loki_protection_is_identity_bound_and_only_adds_a_replica() -> None:
    play = yaml.safe_load(PLAYBOOK.read_text())[0]
    tasks = play["tasks"]

    assert play["hosts"] == "kube_control_plane[0]"
    assert play["vars"]["loki_claim_uid"] == "c43a407a-b315-458d-b6ab-a73aa882c0fb"
    assert play["vars"]["loki_volume"] == "pvc-c43a407a-b315-458d-b6ab-a73aa882c0fb"
    assert play["vars"]["removal_target"] == "node-2"

    patch = task_by_name(tasks, "Add one native Loki replica")["kubernetes.core.k8s_json_patch"][
        "patch"
    ]
    assert patch[-1] == {
        "op": "replace",
        "path": "/spec/numberOfReplicas",
        "value": 2,
    }
    assert {entry["path"] for entry in patch[:-1]} == {"/metadata/uid", "/spec"}

    text = PLAYBOOK.read_text()
    assert "state: absent" not in text
    assert "kind: Replica\n" in text
    assert "kubernetes.core.k8s:" not in text
