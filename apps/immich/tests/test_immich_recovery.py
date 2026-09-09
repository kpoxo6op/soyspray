"""Check rendered isolation, cleanup guards, and failed runner cleanup."""

from pathlib import Path

import jinja2
import pytest
import yaml
from ansible.plugins.filter.core import FilterModule

from apps.immich.recovery import run
from scripts import restore_common

RECOVERY = Path(__file__).resolve().parents[1] / "recovery"


def render(name):
    values = yaml.safe_load((RECOVERY / "restore.yml").read_text())[0]["vars"]
    values.update(
        recovery_namespace="immich-recovery-test",
        recovery_check_id="test",
        recovery_db_password="scratch-password-only",
        recovery_labels={},
        recovery_server_image_digest="ghcr.io/immich-app/immich-server:v2.3.1@sha256:" + "a" * 64,
        recovery_restic_credentials={
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "test",
            "RESTIC_REPOSITORY": "s3:test",
            "RESTIC_PASSWORD": "test",
        },
    )
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters.update(FilterModule().filters())
    return list(yaml.safe_load_all(env.from_string((RECOVERY / name).read_text()).render(values)))


def test_all_templates_render_without_missing_inputs():
    for path in RECOVERY.glob("*.j2"):
        assert all(
            resource["kind"] and resource["metadata"]["name"] for resource in render(path.name)
        )


def test_only_restic_pods_can_reach_public_https():
    policies = [item for item in render("workspace.yaml.j2") if item["kind"] == "NetworkPolicy"]
    public = [
        (policy, peer)
        for policy in policies
        for rule in policy["spec"].get("egress", [])
        for peer in rule.get("to", [])
        if peer.get("ipBlock", {}).get("cidr") == "0.0.0.0/0"
    ]
    assert len(public) == 1
    policy, peer = public[0]
    assert policy["spec"]["podSelector"] == {
        "matchLabels": {"soyspray.vip/component": "restic-restore"}
    }
    assert policy["spec"]["egress"][0]["ports"] == [{"protocol": "TCP", "port": 443}]
    assert {"10.0.0.0/8", "192.168.0.0/16", "100.64.0.0/10"} <= set(peer["ipBlock"]["except"])
    assert any(
        policy["spec"] == {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]}
        for policy in policies
    )


def test_restore_verifies_files_and_excludes_pending_candidates():
    job = render("restore-job.yaml.j2")[0]
    container = job["spec"]["template"]["spec"]["containers"][0]
    command = container["args"][0]
    assert "restic restore --verify" in command
    assert 'index("pending")' in command
    assert 'test "$snapshot_time" = "$dump_time"' in command
    assert not job["spec"]["template"]["spec"]["automountServiceAccountToken"]


def test_recovery_uses_off_cluster_inputs_and_no_production_affinity():
    play = yaml.safe_load((RECOVERY / "restore.yml").read_text())[0]
    serialized = yaml.safe_dump(play)
    assert "recovery_source_secret_result" not in serialized
    assert "recovery_production_before" not in serialized
    assert "recovery_pod_affinity" not in serialized
    assert "namespace: immich\n" not in serialized
    for template in RECOVERY.glob("*.j2"):
        assert "affinity:" not in template.read_text()


def test_runtime_images_are_digest_pinned():
    values = yaml.safe_load((RECOVERY / "restore.yml").read_text())[0]["vars"]
    for name in [
        "recovery_restic_image",
        "recovery_database_image",
        "recovery_redis_image",
        "recovery_probe_image",
    ]:
        assert "@sha256:" in values[name]


def test_immich_requires_explicit_target_paths_before_preflight(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("SOYSPRAY_RECOVERY_KUBECONFIG", raising=False)
    monkeypatch.delenv("SOYSPRAY_RECOVERY_INVENTORY", raising=False)
    operation = restore_common.RestoreOperation(
        "immich",
        tmp_path / "checkout",
        tmp_path / "backup.vault.yml",
        tmp_path / "vault-password",
        explicit_target=True,
    )

    with pytest.raises(ValueError, match="explicit recovery target"):
        operation.prepare()

    assert not operation.created_output
    assert "explicit_target=True" in (RECOVERY / "run.py").read_text()


def test_cleanup_is_idempotent_and_uses_uid_preconditions():
    tasks = yaml.safe_load((RECOVERY / "cleanup.yml").read_text())[0]["tasks"]
    delete = next(
        task for task in tasks if task.get("kubernetes.core.k8s", {}).get("state") == "absent"
    )
    assert delete["when"] == "recovery_namespace_result.resources | length == 1"
    assert "uid" in delete["kubernetes.core.k8s"]["delete_options"]["preconditions"]
    assert tasks[-1]["kubernetes.core.k8s_info"]["kind"] == "PersistentVolume"
    assert "recovery_namespace" in tasks[-1]["until"]


def test_private_report_follows_storage_cleanup():
    tasks = yaml.safe_load((RECOVERY / "restore.yml").read_text())[0]["tasks"]
    always = next(task["always"] for task in tasks if "always" in task)
    report = next(i for i, task in enumerate(always) if "ansible.builtin.copy" in task)
    storage = next(
        i
        for i, task in enumerate(always)
        if task.get("kubernetes.core.k8s_info", {}).get("kind") == "PersistentVolume"
    )
    assert storage < report
    assert always[report]["become"] is False
    assert always[report]["ansible.builtin.copy"]["mode"] == "0600"


def test_failed_restore_runs_guarded_cleanup_without_production_reads(tmp_path):
    calls = []

    class Operation:
        check_id = "test"
        report = {}
        output = tmp_path

        def kube(self, *args):
            raise AssertionError("production reads are disabled by default")

        def vault(self):
            return {
                "immich_restic_credentials": {
                    "AWS_ACCESS_KEY_ID": "test",
                    "AWS_SECRET_ACCESS_KEY": "test",
                    "AWS_DEFAULT_REGION": "test",
                    "RESTIC_REPOSITORY": "s3:test",
                    "RESTIC_PASSWORD": "test",
                }
            }

        def ansible(self, path, variables, log):
            calls.append(Path(path).name)
            if log == "restore.log":
                raise RuntimeError("injected failure")

    operation = Operation()
    with pytest.raises(RuntimeError, match="injected failure"):
        run.restore(operation)
    assert calls == ["restore.yml", "cleanup.yml"]
    assert operation.report["cleanup"] == "completed"
    assert operation.report["production_comparison"] == "not requested"


def test_ansible_preserves_restored_count_list(tmp_path):
    import subprocess
    import sys

    tasks = yaml.safe_load((RECOVERY / "restore.yml").read_text())[0]["tasks"]
    block = next(task["block"] for task in tasks if "block" in task)
    fact = next(
        task["ansible.builtin.set_fact"]
        for task in block
        if "recovery_counts" in task.get("ansible.builtin.set_fact", {})
    )
    play = [
        {
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "vars": {"recovery_database_log": {"log": "ALTER ROLE\ndatabase_counts=0,0,1\n"}},
            "tasks": [
                {"ansible.builtin.set_fact": fact},
                {"ansible.builtin.assert": {"that": ["recovery_counts == ['0', '0', '1']"]}},
            ],
        }
    ]
    path = tmp_path / "counts.yml"
    path.write_text(yaml.safe_dump(play))
    subprocess.run(
        [
            str(Path(sys.executable).with_name("ansible-playbook")),
            "-i",
            "localhost,",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
