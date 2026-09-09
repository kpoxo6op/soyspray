import subprocess
import sys
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
    base = ROOT / "apps/immich/database/immich-db/overlays/initdb"
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


def test_immich_database_apps_are_direct_and_non_pruning():
    expected = {
        "immich-db.yaml": ("immich-db-a-initdb", "apps/immich/database/production"),
        "immich-db-alias.yaml": ("immich-db-active-a", "apps/immich/database/alias"),
    }
    for filename, (name, path) in expected.items():
        app = yaml.safe_load((ROOT / "argocd/catalog" / filename).read_text())
        assert app["kind"] == "Application"
        assert app["metadata"]["name"] == name
        assert app["metadata"]["annotations"]["argocd.argoproj.io/sync-options"] == (
            "Prune=false,Delete=false"
        )
        assert app["spec"]["sources"] == [
            {
                "repoURL": "https://github.com/kpoxo6op/soyspray.git",
                "targetRevision": "main",
                "path": path,
            }
        ]
        assert "automated" not in app["spec"]["syncPolicy"]


def test_immich_adoption_is_exact_guarded_orphan_deletion():
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/adopt-immich-database.yml").read_text()
    )[0]
    assert play["vars"]["expected_root_revision"] == ""
    assert [item["uid"] for item in play["vars"]["owning_sets"]] == [
        "84c8b489-c979-4a50-8896-22ca53aad2e0",
        "a40af192-fb57-40bc-9275-f27b64296b07",
    ]
    drift_task = next(
        task
        for task in play["tasks"]
        if task["name"].startswith("Require only the expected ownership drift")
    )
    assert drift_task["vars"]["expected_drift_names"] == [
        "immich-db",
        "immich-db-a-initdb",
        "immich-db-active-a",
        "immich-db-alias",
    ]
    assert "root_drift | length == 4" in drift_task["ansible.builtin.assert"]["that"]
    deletion = next(
        task["kubernetes.core.k8s"]
        for task in play["tasks"]
        if task["name"].startswith("Orphan the child Applications")
    )
    assert deletion["kind"] == "ApplicationSet"
    assert deletion["state"] == "absent"
    assert deletion["delete_options"] == {"propagationPolicy": "Orphan"}
    identity_guard = next(
        task["ansible.builtin.assert"]["that"]
        for task in play["tasks"]
        if task["name"].startswith("Require unchanged resource identity")
    )
    assert "item.resources[0].metadata.uid == item.item.uid" in identity_guard
    assert (
        "item.resources[0].metadata.ownerReferences | default([]) | length == 0" in identity_guard
    )


def test_authentik_preserves_archive_and_replication():
    resources = list(
        yaml.safe_load_all((ROOT / "apps/authentik-postgresql/manifests/cluster.yaml").read_text())
    )
    cluster, schedule = resources
    assert cluster["spec"]["instances"] == 2
    assert cluster["spec"]["imageName"] == "ghcr.io/cloudnative-pg/postgresql:17.5"
    assert cluster["spec"]["plugins"][0]["parameters"] == {
        "barmanObjectName": "authentik-offsite",
        "serverName": "authentik-postgresql",
    }
    assert cluster["spec"]["backup"] == {"target": "prefer-standby"}
    assert cluster["spec"]["postgresql"]["parameters"]["archive_timeout"] == "5min"
    assert schedule["spec"]["schedule"] == "0 30 3 * * *"
    assert schedule["spec"]["method"] == "plugin"


def test_authentik_policy_renders_as_a_mapping_in_ansible(tmp_path):
    play = yaml.safe_load(
        (ROOT / "playbooks/operations/recovery/select-authentik-database.yml").read_text()
    )[0]
    expression = play["tasks"][2]["kubernetes.core.k8s_json_patch"]["patch"][2]["value"]
    policy = {
        "automated": {"prune": True, "selfHeal": True},
        "syncOptions": ["CreateNamespace=true"],
    }
    tasks = []
    for revision in ["codex/preview", "main"]:
        expected = policy if revision == "main" else {"syncOptions": ["CreateNamespace=true"]}
        tasks.extend(
            [
                {
                    "ansible.builtin.set_fact": {"selected_policy": expression},
                    "vars": {"cnpg_revision": revision},
                },
                {
                    "ansible.builtin.assert": {
                        "that": ["selected_policy is mapping", "selected_policy == expected"]
                    },
                    "vars": {"expected": expected},
                },
            ]
        )
    path = tmp_path / "policy.yml"
    path.write_text(
        yaml.safe_dump(
            [
                {
                    "hosts": "localhost",
                    "gather_facts": False,
                    "vars": {"app": {"resources": [{"spec": {"syncPolicy": policy}}]}},
                    "tasks": tasks,
                }
            ]
        )
    )
    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("ansible-playbook")),
            "-i",
            "localhost,",
            "-c",
            "local",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
