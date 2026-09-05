import base64
import copy
import importlib
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize(
    "failure", [None, "preflight", "restore", "data", "start", "original", "cleanup"]
)
def test_restore_operation_cleans_up_after_failures_and_never_reports_partial_success(
    tmp_path, monkeypatch, capsys, failure
):
    import json
    import os
    import subprocess
    import sys

    restore_check = importlib.import_module("apps.obsidian-livesync.restore_check")

    root = tmp_path / "checkout"
    root.mkdir()
    vault = tmp_path / "runtime.vault.yml"
    vault.write_text("$ANSIBLE_VAULT;synthetic")
    password = tmp_path / "password"
    password.write_text("synthetic")
    monkeypatch.setattr(restore_check, "ROOT", root)
    monkeypatch.setattr(
        sys,
        "argv",
        ["restore-check", "--vault-file", str(vault), "--vault-password-file", str(password)],
    )
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    image = "docker.io/library/couchdb@sha256:" + "a" * 64
    claim = {
        "metadata": {"uid": "claim-uid"},
        "spec": {"volumeName": "pvc-original", "storageClassName": "longhorn"},
        "status": {"phase": "Bound"},
    }
    volume = {
        "metadata": {"uid": "volume-uid"},
        "spec": {
            "claimRef": {"uid": "claim-uid"},
            "csi": {"driver": "driver.longhorn.io", "volumeHandle": "pvc-original"},
        },
    }
    deployment = {
        "metadata": {"uid": "deployment-uid"},
        "spec": {
            "replicas": 1,
            "strategy": {"type": "Recreate"},
            "selector": {"matchLabels": {"app": "couchdb"}},
        },
    }
    inputs = {
        "adminUsername": "synthetic-user",
        "adminPassword": "synthetic-identity-with-no-live-access",
        "cookieAuthSecret": "synthetic-cookie",
        "erlangCookie": "synthetic-erlang",
    }
    secret = {
        "metadata": {"uid": "secret-uid"},
        "data": {key: base64.b64encode(value.encode()).decode() for key, value in inputs.items()},
    }
    config = {"metadata": {"uid": "config-uid"}, "data": {"inifile": "synthetic-config"}}
    config_path = root / "apps/obsidian-livesync/manifests/configmap-couchdb.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(yaml.safe_dump(config))
    pod = {
        "metadata": {"name": "couchdb"},
        "spec": {"containers": [{"name": "couchdb", "image": image}]},
        "status": {"containerStatuses": [{"name": "couchdb", "imageID": image, "ready": True}]},
    }
    operations = []
    volume_reads = 0

    def read(args, **kwargs):
        nonlocal volume_reads
        if args[:2] == ["git", "rev-parse"]:
            return "source-commit\n"
        if "view" in args:
            value = (
                {"contexts": []} if args[0] == "kubectl" else {"obsidian_couchdb_identity": inputs}
            )
        else:
            kubeconfig = Path(kwargs["env"]["KUBECONFIG"])
            assert kubeconfig.stat().st_mode & 0o777 == 0o600
            if "pvc" in args:
                value = (
                    {"metadata": {"uid": "restored-uid"}, "spec": {"volumeName": "isolated"}}
                    if "restored-data" in args
                    else claim
                )
            elif "pv" in args:
                volume_reads += 1
                value = copy.deepcopy(volume)
                if failure == "original" and volume_reads > 1:
                    value["metadata"]["uid"] = "replacement"
            elif "backups.longhorn.io" in args:
                value = {
                    "items": [
                        {
                            "metadata": {"name": "backup", "uid": "backup-uid"},
                            "status": {
                                "volumeName": "pvc-original",
                                "backupTargetName": "critical-s3",
                                "state": "Completed",
                                "progress": 100,
                                "snapshotCreatedAt": "2020-01-01T00:00:00Z",
                                "url": "s3://example/backup",
                            },
                        }
                    ]
                }
            elif "secret" in args:
                value = secret
            elif "configmap" in args:
                value = config
            elif "deployment" in args:
                value = deployment
            elif "pods" in args:
                value = {"items": [pod]}
            else:
                raise AssertionError(args)
        return json.dumps(value).encode()

    def run(args, **kwargs):
        if args[0] == "make":
            assert args == ["make", "go"]
            if failure == "preflight":
                raise subprocess.CalledProcessError(2, args)
        elif str(args[0]).endswith("ansible-playbook"):
            assert args[-1].startswith("@")
            private = Path(args[-1][1:])
            assert private.stat().st_mode & 0o777 == 0o600
            variables = json.loads(private.read_text())
            assert "synthetic-identity-with-no-live-access" not in str(args)
            assert variables["recovery_resources"][0]["data"] == secret["data"]
            assert variables["recovery_expected_claim_uid"] == "claim-uid"
            assert variables["recovery_expected_backup_uid"] == "backup-uid"
            action = (
                "cleanup"
                if "cleanup-restore.yml" in args[-3]
                else "start"
                if "start-restored-app.yml" in args[-3]
                else "restore"
            )
            operations.append(action)
            if failure == action:
                raise subprocess.CalledProcessError(2, args)
        return subprocess.CompletedProcess(args, 0)

    def check_notes(*args):
        assert args[-1] == inputs
        if failure == "data":
            raise ValueError("Synthetic invalid note data")
        return {"couchdb_authenticated_read": True, "readable_plain_notes": 1}

    monkeypatch.setattr(restore_check, "check_restored_notes", check_notes)
    monkeypatch.setattr(restore_check.subprocess, "check_output", read)
    monkeypatch.setattr(restore_check.subprocess, "run", run)
    old_umask = os.umask(0o077)
    try:
        code = restore_check.main()
    finally:
        os.umask(old_umask)
    reports = list((tmp_path / "state").rglob("report.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text())
    assert reports[0].stat().st_mode & 0o777 == 0o600
    assert report["status"] == ("failed" if failure else "passed")
    assert code == (2 if failure else 0)
    assert operations == (
        []
        if failure == "preflight"
        else ["restore", "cleanup"]
        if failure == "restore"
        else ["restore", "start", "cleanup"]
    )
    assert report["cleanup"] == (
        "not started"
        if failure == "preflight"
        else "failed - inspect the guarded cleanup log"
        if failure == "cleanup"
        else "completed"
    )
    assert not list(reports[0].parent.glob("working-*"))
    assert "synthetic-identity-with-no-live-access" not in capsys.readouterr().out


@pytest.mark.parametrize("change", ["missing", "changed", "non-string"])
def test_archived_couchdb_identity_must_match_before_restore(change):
    restore = importlib.import_module("apps.obsidian-livesync.restore_check")
    values = {
        key: "synthetic"
        for key in ("adminUsername", "adminPassword", "cookieAuthSecret", "erlangCookie")
    }
    secret = {
        "data": {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}
    }
    assert restore.runtime_values({"obsidian_couchdb_identity": values}, secret) == values
    if change == "missing":
        values.pop("erlangCookie")
    else:
        values["adminPassword"] = None if change == "non-string" else "different"
    with pytest.raises(ValueError):
        restore.runtime_values({"obsidian_couchdb_identity": values}, secret)


@pytest.mark.parametrize(
    "image,accepted",
    [
        ("couchdb@sha256:" + "a" * 64, True),
        ("docker.io/library/couchdb:3.4.2@sha256:" + "a" * 64, True),
        ("couchdb:3.4.2", False),
        ("dockerXio/library/couchdb@sha256:" + "a" * 64, False),
        ("custom/couchdb@sha256:" + "a" * 64, False),
        ("", False),
    ],
)
def test_native_restore_requires_a_pinned_stock_couchdb_image(image, accepted):
    from ansible.parsing.dataloader import DataLoader
    from ansible.playbook.conditional import Conditional
    from ansible.template import Templar

    root = Path(__file__).resolve().parents[3]
    tasks = yaml.safe_load(
        (root / "playbooks/operations/recovery/start-restored-app.yml").read_text()
    )[0]["tasks"]
    guard = next(
        condition
        for task in tasks
        for condition in task.get("ansible.builtin.assert", {}).get("that", [])
        if "recovery_couchdb_image" in condition
    )
    variables = {"recovery_couchdb_image": image}
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = [guard]
    assert (
        condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
        is accepted
    )
