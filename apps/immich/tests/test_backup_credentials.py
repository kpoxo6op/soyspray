import base64
import copy
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("backup_credentials", ROOT / "backup/credentials.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def encode(values):
    return {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}


@pytest.fixture
def inputs():
    return {
        "restic": dict(
            AWS_ACCESS_KEY_ID="fixture-id",
            AWS_SECRET_ACCESS_KEY="fixture-key",
            AWS_DEFAULT_REGION="ap-southeast-2",
            RESTIC_PASSWORD="fixture-password",
            RESTIC_REPOSITORY="s3:s3.ap-southeast-2.amazonaws.com/soyspray-recovery-au2-403732031071/immich",
        ),
        "deployment": {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "env": [
                                    {"name": "DB_HOSTNAME", "value": "obsolete-host"},
                                    {
                                        "name": "DB_URL",
                                        "value": "postgresql://immich:fixture%40password@immich-db-active.postgresql.svc.cluster.local:5432/immich",
                                    },
                                ]
                            }
                        ]
                    }
                }
            }
        },
        "database_secret": {"data": encode({"username": "immich", "password": "fixture@password"})},
        "existing": [],
    }


def test_authoritative_connection_and_repeat_preserve_all_inputs(inputs):
    before = copy.deepcopy(inputs)
    result = module.credentials(inputs)
    assert inputs == before
    assert result["PGHOST"] == "immich-db-active.postgresql.svc.cluster.local"
    assert result["PGPASSWORD"] == "fixture@password"
    inputs["existing"] = [{"data": encode(result)}]
    assert module.credentials(inputs) == result


@pytest.mark.parametrize(
    "change", ["password", "host", "missing_url", "wrong_store", "typed", "missing", "existing"]
)
def test_reject_invalid_or_changed_identity(inputs, change):
    if change == "password":
        inputs["database_secret"]["data"]["password"] = encode({"p": "different"})["p"]
    elif change == "host":
        env = inputs["deployment"]["spec"]["template"]["spec"]["containers"][0]["env"][1]
        env["value"] = env["value"].replace("immich-db-active", "other")
    elif change == "missing_url":
        inputs["deployment"]["spec"]["template"]["spec"]["containers"][0]["env"].pop()
    elif change == "wrong_store":
        inputs["restic"]["RESTIC_REPOSITORY"] += "-different"
    elif change == "typed":
        inputs["restic"]["RESTIC_PASSWORD"] = 123
    elif change == "missing":
        inputs["restic"].pop("AWS_ACCESS_KEY_ID")
    else:
        saved = module.credentials(inputs)
        saved["RESTIC_PASSWORD"] = "different"
        inputs["existing"] = [{"data": encode(saved)}]
    with pytest.raises(ValueError):
        module.credentials(inputs)


def test_bootstrap_validates_privately_before_create_only_write():
    tasks = yaml.safe_load((ROOT / "backup/bootstrap.yml").read_text())[0]["tasks"]
    assert all(task["no_log"] is True for task in tasks)
    assert [task["kubernetes.core.k8s_info"]["name"] for task in tasks[:3]] == [
        "immich-server",
        "immich-app-secret-a",
        "immich-paired-backup",
    ]
    assert tasks[3]["check_mode"] is False
    assert tasks[3]["changed_when"] is False
    assert tasks[4]["ansible.builtin.command"]["argv"][-3:] == ["create", "-f", "-"]
    assert (
        tasks[4]["when"]
        == "immich_backup_existing.resources | length == 0 and not ansible_check_mode"
    )


def test_manual_job_is_suspended_guarded_and_always_cleans_up():
    tasks = yaml.safe_load((ROOT / "backup/run-job.yml").read_text())[0]["tasks"]
    assertions = [
        task["ansible.builtin.assert"]["that"] for task in tasks if "ansible.builtin.assert" in task
    ]
    assert "immich_backup_cron.resources[0].spec.suspend | bool" in assertions[1]
    assert "immich_backup_existing_job.resources | length == 0" in assertions[1]
    operation = next(task for task in tasks if "block" in task)
    job = operation["block"][0]["kubernetes.core.k8s"]["definition"]
    assert job["spec"]["backoffLimit"] == 0
    assert job["metadata"]["namespace"] == "immich"
    assert job["metadata"]["labels"]["soyspray.vip/run-id"] == "{{ immich_backup_run_id }}"
    cleanup = operation["always"][0]["always"][0]["kubernetes.core.k8s"]
    assert cleanup["state"] == "absent"
    assert cleanup["delete_options"]["propagationPolicy"] == "Foreground"
    assert (
        cleanup["delete_options"]["preconditions"]["uid"]
        == "{{ immich_backup_created_job.result.metadata.uid }}"
    )
    assert cleanup["wait"] is True
