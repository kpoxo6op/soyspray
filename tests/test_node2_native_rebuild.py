from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "playbooks/operations/nodes"


def test_remove_node2_is_a_preflight_only_playbook() -> None:
    plays = yaml.safe_load((NODES / "remove-node2.yml").read_text())
    assert [play["ansible.builtin.import_playbook"] for play in plays] == [
        "preflight-node2-removal.yml",
    ]
    for play in plays:
        assert play["vars"] == {
            "node": "node-2",
            "reset_nodes": True,
            "allow_ungraceful_removal": False,
            "skip_confirmation": True,
            "flush_iptables": False,
            "reset_restart_network": False,
        }

    text = (NODES / "remove-node2.yml").read_text()
    assert "--limit" not in text
    assert "reset.yml" not in text
    assert "../../../kubespray/remove-node.yml" not in text


def test_removal_preflight_requires_real_recovery_evidence() -> None:
    text = (NODES / "preflight-node2-removal.yml").read_text()
    for required in (
        "node2_evacuation_evidence_file",
        "node2_etcd_snapshot_file",
        "node2_etcd_snapshot_sha256",
        "node2_backup_evidence_file",
        "node2_immich_restore_report",
        "origin/main",
        "asset_count | int > 0",
        "production_inputs == 'not read'",
        "allow_ungraceful_removal | default(true)",
        "value is number",
        "node2_backup_observed_epoch",
        "BackingImageManager",
        "validate-node2-cnpg.yml",
        "node2_retired_volume_uid: 572e059e-7d02-4e03-afcf-bf75cefed4b7",
        "status.currentState', 'equalto', 'running'",
    ):
        assert required in text

    plays = yaml.safe_load(text)
    assert all(play.get("any_errors_fatal") is True for play in plays)


def test_identity_probes_run_in_check_mode_with_exact_findmnt_columns() -> None:
    for name in ("preflight-node2-removal.yml", "clean-node2-baseline.yml", "rejoin-node2.yml"):
        text = (NODES / name).read_text()
        assert '[findmnt, -J, -o, "SOURCE,TARGET,FSTYPE,UUID"' in text
        assert "check_mode: false" in text


def test_cleanup_requires_stopped_services_and_real_paths_before_deletion() -> None:
    text = (NODES / "clean-node2-baseline.yml").read_text()
    service_check = text.index("Read cluster service states before cleanup")
    replica_delete = text.index("Remove only recorded Longhorn replica directories")
    assert service_check < replica_delete
    assert "realpath, --canonicalize-missing" in text
    assert "^/storage/replicas/pvc-" in text


def test_baseline_cleanup_can_only_target_cluster_network_prefixes() -> None:
    script = (NODES / "cleanup-kubernetes-network.py").read_text()
    assert 'CHAIN_PREFIXES = ("KUBE-", "cali-")' in script
    assert 'IPSET_PREFIXES = ("KUBE-", "cali")' in script
    assert "iptables-restore" not in script
    assert "ip6tables-restore" not in script
    assert "flush_iptables" not in script
    for unsafe in ("mkfs", "wipefs", "parted", "reboot"):
        assert unsafe not in script

    playbook = (NODES / "clean-node2-baseline.yml").read_text()
    assert 'path: "/storage/replicas/{{ item }}"' in playbook
    assert "expected_root_uuid: d3507a31-6115-4f40-affc-ca5164120e50" in playbook
    assert "expected_storage_uuid: 49c092f4-dd55-41f5-99c6-854f8b44af4e" in playbook


def test_rejoin_uses_existing_storage_and_full_kubespray_cluster_play() -> None:
    plays = yaml.safe_load((NODES / "rejoin-node2.yml").read_text())
    imports = [
        play["ansible.builtin.import_playbook"]
        for play in plays
        if "ansible.builtin.import_playbook" in play
    ]
    assert imports == [
        "../storage/prepare-existing-longhorn-storage.yml",
        "../../../kubespray/cluster.yml",
    ]
    kubespray_import = next(
        play
        for play in plays
        if play.get("ansible.builtin.import_playbook") == "../../../kubespray/cluster.yml"
    )
    assert kubespray_import["when"] == "not ansible_check_mode"
    text = (NODES / "rejoin-node2.yml").read_text()
    assert "--limit" not in text
    assert "ignore_assert_errors | default(false)" in text
    assert "kubernetes_node_uid" in text
    assert "node2_survivor_cluster_id" in text
    assert all(
        play.get("any_errors_fatal") is True
        for play in plays
        if "ansible.builtin.import_playbook" not in play
    )

    post_rejoin = plays[-1]["tasks"]
    assert all(task.get("when") == "not ansible_check_mode" for task in post_rejoin)


def test_restart_respects_native_eviction_protection() -> None:
    text = (NODES / "restart-node.yml").read_text()
    assert "kubectl drain" in text
    assert "--disable-eviction" not in text


def test_controller_installs_the_pinned_kubespray_collections() -> None:
    requirements = yaml.safe_load((ROOT / "requirements-ansible.yml").read_text())
    versions = {item["name"]: item["version"] for item in requirements["collections"]}
    assert versions == {
        "ansible.netcommon": "5.3.0",
        "ansible.posix": "1.5.4",
        "ansible.utils": "2.7.0",
        "community.crypto": "2.22.3",
        "community.docker": "3.11.0",
        "community.general": "7.0.0",
        "community.library_inventory_filtering_v1": "1.1.5",
        "kubernetes.core": "5.4.1",
    }
