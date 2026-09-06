from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RESTORE = ROOT / "recovery" / "restore.yml"
CLEANUP = ROOT / "recovery" / "cleanup.yml"


def _tasks(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())[0]["tasks"]


def _block(path: Path) -> list[dict]:
    return _tasks(path)[-1]["block"]


def test_restore_observes_production_identity_before_and_after() -> None:
    tasks = _tasks(RESTORE)
    reads = [task for task in tasks if "kubernetes.core.k8s_info" in task]
    assert len(reads) == 3
    before = reads[0]["loop"]
    after = next(
        task["loop"]
        for task in _block(RESTORE)
        if "kubernetes.core.k8s_info" in task
        and task.get("register") == "recovery_production_after"
    )
    assert before == after
    assert {item["name"] for item in before} == {
        "immich-server",
        "immich-library",
        "immich-db-active",
        "immich-db",
    }
    after_check = _block(RESTORE)[-2]
    assert "metadata.uid == recovery_production_before" in str(after_check)
    assert "spec.volumeName" in str(after_check)


def test_restore_selects_completed_candidates_and_hashes_all_files() -> None:
    block = _block(RESTORE)
    restore = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("metadata", {}).get("name")
        == "restic-restore"
    )
    command = restore["kubernetes.core.k8s"]["definition"]["spec"]["template"]["spec"][
        "containers"
    ][0]["args"][0]
    assert "--host {{ recovery_snapshot_host }} --tag {{ recovery_snapshot_tag }}" in command
    assert "map(select(" in command
    assert ".hostname ==" in command
    assert 'restic restore "$id" --target /restore' in command
    verify = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("metadata", {}).get("name")
        == "restic-verify"
    )
    verify_command = verify["kubernetes.core.k8s"]["definition"]["spec"]["template"]["spec"][
        "containers"
    ][0]["args"][0]
    assert 'restic dump "$id" "$path"' in verify_command
    assert 'sha256sum "/restore$path"' in verify_command
    assert 'type == "file"' in verify_command


def test_restore_runs_version_matched_isolated_services_without_ingress() -> None:
    block = _block(RESTORE)
    db = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("kind") == "Cluster"
    )
    db_spec = db["kubernetes.core.k8s"]["definition"]
    assert db_spec["metadata"]["namespace"] == "{{ recovery_namespace }}"
    assert db_spec["spec"]["imageName"] == "{{ recovery_database_image }}"
    redis = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("metadata", {}).get("name")
        == "redis"
    )
    assert redis["kubernetes.core.k8s"]["definition"]["spec"]["containers"][0]["image"] == (
        "{{ recovery_redis_image }}"
    )
    server = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("metadata", {}).get("name")
        == "immich-server"
    )
    server_spec = server["kubernetes.core.k8s"]["definition"]["spec"]
    assert server_spec["containers"][0]["image"] == "{{ recovery_server_image }}"
    assert server_spec["containers"][0]["volumeMounts"] == [
        {"name": "restored-data", "mountPath": "/usr/src/app/upload"}
    ]
    service = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("kind") == "Service"
        and task["kubernetes.core.k8s"]["definition"]["metadata"]["name"] == "immich-server"
    )
    assert service["kubernetes.core.k8s"]["definition"]["spec"]["type"] == "ClusterIP"
    policy = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("kind") == "NetworkPolicy"
    )
    assert policy["kubernetes.core.k8s"]["definition"]["spec"]["policyTypes"] == ["Ingress"]
    assert policy["kubernetes.core.k8s"]["definition"]["spec"]["ingress"] == [
        {"from": [{"podSelector": {}}]}
    ]


def test_restore_compares_database_content_and_internal_health() -> None:
    block = _block(RESTORE)
    database = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("metadata", {}).get("name")
        == "database-restore"
    )
    command = database["kubernetes.core.k8s"]["definition"]["spec"]["template"]["spec"][
        "containers"
    ][0]["args"][0]
    assert "pg_restore --exit-on-error" in command
    assert "immich_snapshot" in command
    assert "md5(coalesce(string_agg" in command
    assert "diff -u" in command
    health = next(
        task
        for task in block
        if task.get("kubernetes.core.k8s", {}).get("definition", {}).get("metadata", {}).get("name")
        == "app-health"
    )
    health_command = health["kubernetes.core.k8s"]["definition"]["spec"]["template"]["spec"][
        "containers"
    ][0]["args"][0]
    assert "/api/server/ping" in health_command
    assert "/api/server/version" in health_command


def test_cleanup_requires_matching_labels_and_uid() -> None:
    tasks = _tasks(CLEANUP)
    checks = [task for task in tasks if "ansible.builtin.assert" in task]
    assert any("soyspray.vip/purpose" in str(task) for task in checks)
    delete = next(
        task
        for task in tasks
        if task.get("kubernetes.core.k8s", {}).get("state") == "absent"
        and task["kubernetes.core.k8s"].get("kind") == "Namespace"
    )
    options = delete["kubernetes.core.k8s"]["delete_options"]
    assert (
        options["preconditions"]["uid"]
        == "{{ recovery_namespace_result.resources[0].metadata.uid }}"
    )
