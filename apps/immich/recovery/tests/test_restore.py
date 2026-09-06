from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
RECOVERY = ROOT / "recovery"


def _playbook(name: str) -> list[dict]:
    return yaml.safe_load((RECOVERY / name).read_text())[0]["tasks"]


def test_preflight_uses_live_a_database_and_alias_target() -> None:
    text = (RECOVERY / "restore.yml").read_text()
    assert "name: immich-db-a" in text
    assert "immich-db-a-rw.postgresql.svc.cluster.local" in text
    assert "kind: Cluster, namespace: postgresql, name: immich-db}" not in text


def test_workspace_denies_cluster_egress_before_workloads() -> None:
    text = (RECOVERY / "workspace.yaml.j2").read_text()
    assert text.index("name: default-deny") < text.index("kind: PersistentVolumeClaim")
    assert "policyTypes: [Ingress, Egress]" in text
    assert "except: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]" in text


def test_restic_restore_creates_backup_dir_and_uses_verify() -> None:
    text = (RECOVERY / "restore-job.yaml.j2").read_text()
    assert "mkdir -p /restore/backup" in text
    assert "restic restore --verify" in text
    assert "restic dump" not in text
    assert "restic ls" not in text
    assert "RESTIC_PASSWORD_FILE, value: /run/secrets/restic-password/RESTIC_PASSWORD" in text
    assert "mountPath: /run/secrets/restic-password," in text


def test_database_has_credentials_and_restore_capable_extension_owner() -> None:
    text = (RECOVERY / "database.yaml.j2").read_text()
    assert "name: immich-db-credentials" in text
    assert "owner: {{ recovery_db_username }}" in text
    assert "ALTER ROLE {{ recovery_db_username }} CREATEDB" in text
    assert "CREATE EXTENSION IF NOT EXISTS vectors" in text
    assert "imageName: {{ recovery_database_image }}" in text


def test_runtime_uses_subpath_and_internal_services_only() -> None:
    text = (RECOVERY / "runtime.yaml.j2").read_text()
    assert "image: {{ recovery_server_image_digest }}" in text
    assert "mountPath: /usr/src/app/upload, subPath: usr/src/app/upload" in text
    assert text.count("type: ClusterIP") == 2
    assert "kind: Ingress" not in text


def test_cleanup_has_label_and_uid_guard() -> None:
    tasks = _playbook("cleanup.yml")
    check = next(task for task in tasks if "ownership labels" in task.get("ansible.builtin.assert", {}).get("fail_msg", ""))
    assert "soyspray.vip/purpose" in str(check)
    delete = next(task for task in tasks if task.get("kubernetes.core.k8s", {}).get("state") == "absent")
    assert "uid" in delete["kubernetes.core.k8s"]["delete_options"]["preconditions"]


def test_report_is_written_after_namespace_cleanup() -> None:
    tasks = _playbook("restore.yml")
    block_task = next(task for task in tasks if "block" in task)
    names = [task.get("name") for task in block_task["always"]]
    assert names.index("Write the private validated restore report") > names.index("Remove the owned scratch namespace after every real check")
    text = (RECOVERY / "restore.yml").read_text()
    assert "Remove the owned scratch namespace after every real check" in text
    assert "cleanup: completed" in text


def test_signal_wrapper_calls_guarded_cleanup() -> None:
    text = (RECOVERY / "run.sh").read_text()
    assert "trap cleanup_on_signal INT TERM" in text
    assert "cleanup.yml" in text
    assert "recovery_check_id=$check_id" in text
