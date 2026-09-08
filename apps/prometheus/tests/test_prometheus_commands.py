import os
import subprocess
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[3]
STACK_UID = "a58c2137-4482-4926-b659-ad08ab017aed"


def adoption_validation_passes(application):
    play = yaml.safe_load((ROOT / "apps/prometheus/adopt.yml").read_text())[0]
    task = next(task for task in play["tasks"] if "expected Prometheus" in task["name"])
    variables = {
        "item": {
            "resources": [application],
            "item": {"name": "kube-prometheus-stack", "uid": STACK_UID},
        },
        "prometheus_revision": "HEAD",
    }
    loader = DataLoader()
    for name, expression in task["vars"].items():
        variables[name] = Templar(loader=loader, variables=variables).template(expression)
    condition = Conditional(loader=loader)
    condition.when = task["ansible.builtin.assert"]["that"]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


def adopted_stack():
    return {
        "metadata": {"uid": STACK_UID},
        "spec": {
            "project": "prometheus-stack",
            "source": {
                "repoURL": "https://github.com/kpoxo6op/soyspray.git",
                "path": "apps/prometheus",
                "targetRevision": "issue-309-prometheus-native-argo",
            },
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": "monitoring",
            },
        },
    }


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


def test_adopted_preview_can_return_to_head():
    assert adoption_validation_passes(adopted_stack())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("metadata", "uid"), "unexpected"),
        (("metadata", "deletionTimestamp"), "2026-09-09T00:00:00Z"),
        (("spec", "project"), "default"),
        (("spec", "source", "repoURL"), "https://example.test/wrong.git"),
        (("spec", "source", "path"), "apps/wrong"),
        (("spec", "source", "targetRevision"), ""),
        (("spec", "source", "targetRevision"), None),
        (("spec", "destination", "server"), "https://example.test"),
        (("spec", "destination", "namespace"), "default"),
    ],
)
def test_adopted_preview_rejects_wrong_identity_or_ownership(path, value):
    application = adopted_stack()
    selected = application
    for key in path[:-1]:
        selected = selected[key]
    selected[path[-1]] = value
    assert not adoption_validation_passes(application)


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
