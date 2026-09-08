import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_deploy_preserves_identity_then_adopts_and_previews():
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            "apps/prometheus/Makefile",
            "deploy",
            "REVISION=issue-309",
            "ANSIBLE=echo ansible-playbook",
        ],
        cwd=ROOT,
        env=os.environ,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    commands = [line for line in result.stdout.splitlines() if line.startswith("ansible-playbook ")]
    assert commands == [
        "ansible-playbook apps/prometheus/bootstrap.yml",
        "ansible-playbook apps/prometheus/adopt.yml -e prometheus_revision=issue-309 "
        "-e prometheus_stack_uid=a58c2137-4482-4926-b659-ad08ab017aed "
        "-e prometheus_crds_uid=72c2f99a-2820-4751-ac38-42c2097b5504",
        "ansible-playbook playbooks/bootstrap-apps.yml -e argocd_revision=issue-309 "
        "-e argocd_preview_application=kube-prometheus-stack",
    ]


def test_adoption_checks_all_applications_before_removing_only_cascading_finalizers():
    play = yaml.safe_load((ROOT / "apps/prometheus/adopt.yml").read_text())[0]
    tasks = play["tasks"]
    validation = next(task for task in tasks if "expected Prometheus" in task["name"])
    removal = next(
        task for task in tasks if task["name"] == "Remove only cascading deletion finalizers"
    )
    assert tasks.index(validation) < tasks.index(removal)
    checks = validation["ansible.builtin.assert"]["that"]
    assert any("metadata.uid" in check for check in checks)
    assert any("deletionTimestamp" in check for check in checks)
    assert any("destination" in check for check in checks)
    assert any("legacy_stack" in check and "adopted_stack" in check for check in checks)
    assert removal["kubernetes.core.k8s_json_patch"]["patch"][0]["path"] == (
        "/metadata/resourceVersion"
    )
    assert removal["kubernetes.core.k8s_json_patch"]["patch"][1] == {
        "op": "replace",
        "path": "/metadata/finalizers",
        "value": "{{ existing_finalizers | difference(cascading_finalizers) }}",
    }


@pytest.mark.parametrize("action", ["restore-check", "smoke"])
def test_unknown_operations_do_not_run_ansible(tmp_path, action):
    marker = tmp_path / "ansible-ran"
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            "apps/prometheus/Makefile",
            action,
            f"ANSIBLE=touch {marker}",
        ],
        cwd=ROOT,
        env=os.environ,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 2
    assert "unknown:" in result.stderr
    assert not marker.exists()
