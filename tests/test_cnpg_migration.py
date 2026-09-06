from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_archive_switch_is_one_identity_guarded_patch():
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/migrate-cnpg-backup.yml").read_text()
    )[0]
    task = next(t for t in play["tasks"] if "kubernetes.core.k8s_json_patch" in t)
    patch = task["kubernetes.core.k8s_json_patch"]["patch"]
    assert [(p["op"], p["path"]) for p in patch] == [
        ("test", "/metadata/resourceVersion"),
        ("replace", "/spec/backup"),
        ("add", "/spec/plugins"),
    ]
    assert patch[1]["value"] == {"target": "prefer-standby"}
    assert patch[2]["value"][0]["isWALArchiver"] is True
    assert task["when"] == "before.resources[0].spec.backup.barmanObjectStore is defined"
    guard = next(
        t["ansible.builtin.assert"]["that"]
        for t in play["tasks"]
        if "ansible.builtin.assert" in t
        and "before.resources | length == 1" in t["ansible.builtin.assert"]["that"]
    )
    assert "before.resources[0].metadata.uid == db.uid" in guard
    assert "before.resources[0].status.systemID == db.system_id" in guard


def test_immich_preserves_archive_identity_and_daily_schedule():
    base = ROOT / "playbooks/argocd/applications/database/cnpg/immich-db/overlays/initdb"
    spec = yaml.safe_load((base / "backup-config-patch.yaml").read_text())["spec"]
    assert spec["plugins"][0]["parameters"] == {
        "barmanObjectName": "immich-offsite",
        "serverName": "immich-db-a-post-ssd-20260506",
    }
    assert spec["postgresql"]["parameters"]["archive_timeout"] == "5min"
    assert spec["backup"] == {"target": "prefer-standby"}
    schedule = yaml.safe_load((base / "scheduledbackup.yaml").read_text())["spec"]
    assert schedule["method"] == "plugin"
    assert schedule["schedule"] == "0 47 4 * * *"
    assert schedule["target"] == "prefer-standby"


def test_immich_sync_selects_existing_resources_without_pruning():
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/reconcile-immich-database.yml").read_text()
    )[0]
    task = play["tasks"][-1]["kubernetes.core.k8s_json_patch"]
    assert task["patch"][0]["path"] == "/metadata/resourceVersion"
    sync = task["patch"][1]["value"]["sync"]
    assert sync["prune"] is False
    assert sync["resources"] == "{{ item.item.resources }}"
    assert all(
        r["kind"] != "Backup" for group in play["vars"]["cnpg_sets"] for r in group["resources"]
    )
