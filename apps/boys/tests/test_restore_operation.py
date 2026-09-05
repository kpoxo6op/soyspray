import base64
import copy
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

from apps.boys.restore_check import runtime_values, select_backup, verify_binding

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2030, 1, 2, 1, tzinfo=timezone.utc)


def backup(name="good", point="2030-01-02T00:30:00Z", **state):
    return {
        "metadata": {"name": name, "uid": "backup-uid"},
        "status": {
            "volumeName": "pvc-original",
            "backupTargetName": "critical-s3",
            "state": "Completed",
            "progress": 100,
            "snapshotCreatedAt": point,
            "url": "s3://example/backup",
            **state,
        },
    }


@pytest.mark.parametrize(
    "invalid",
    [
        {"state": "Pending"},
        {"progress": 99},
        {"error": "failed"},
        {"messages": {"Error": "failed"}},
        {"volumeName": "other"},
        {"backupTargetName": "other"},
        {"url": ""},
        {"snapshotCreatedAt": "2031-01-01T00:00:00Z"},
        {"snapshotCreatedAt": "2030-01-01T00:00:00"},
        {"snapshotCreatedAt": "not-time"},
        {"snapshotCreatedAt": "1969-01-01T00:00:00Z"},
    ],
)
def test_failed_unfinished_foreign_or_invalid_points_are_not_restore_candidates(invalid):
    good = backup()
    bad = backup("bad", **invalid)
    assert select_backup([bad, good], "pvc-original", NOW) == good
    with pytest.raises(ValueError, match="eligible"):
        select_backup([bad, good], "pvc-original", NOW, "bad")


def test_selection_uses_snapshot_start_and_an_explicit_older_backup():
    old = backup("old", "2030-01-02T00:00:00Z", backupCreatedAt="2030-01-02T00:59:00Z")
    recent = backup("recent", "2030-01-02T00:30:00Z", backupCreatedAt="2030-01-02T00:45:00Z")
    assert select_backup([old, recent], "pvc-original", NOW) == recent
    assert select_backup([old, recent], "pvc-original", NOW, "old") == old


def test_original_claim_uid_and_driver_must_match_the_backing_volume():
    claim = {
        "metadata": {"uid": "original"},
        "spec": {"volumeName": "pvc-original", "storageClassName": "longhorn"},
        "status": {"phase": "Bound"},
    }
    volume = {
        "metadata": {"uid": "volume-uid"},
        "spec": {
            "claimRef": {"uid": "original"},
            "csi": {"driver": "driver.longhorn.io", "volumeHandle": "pvc-original"},
        },
    }
    verify_binding(claim, volume)
    for key, changed in (
        ("claimRef", {"uid": "replacement"}),
        ("csi", {"driver": "other", "volumeHandle": "pvc-original"}),
    ):
        bad = copy.deepcopy(volume)
        bad["spec"][key] = changed
        with pytest.raises(ValueError, match="binding"):
            verify_binding(claim, bad)


def test_archived_session_key_must_match_live_before_testing_a_legacy_token():
    archived = {"boys_pin": "1357", "boys_session_key": "synthetic-key-from-encrypted-archive"}
    live = {
        "data": {
            "pin": base64.b64encode(b"1357").decode(),
            "session-key": base64.b64encode(archived["boys_session_key"].encode()).decode(),
        }
    }
    assert runtime_values(archived, live) == archived
    with pytest.raises(ValueError, match="does not match"):
        runtime_values({**archived, "boys_session_key": "wrong-key"}, live)


@pytest.mark.parametrize(
    "playbook,variable",
    [
        ("restore-volume.yml", "recovery_expected_claim_uid"),
        ("restore-volume.yml", "recovery_expected_backup_uid"),
        ("cleanup-restore.yml", "recovery_expected_backup_uid"),
    ],
)
def test_native_operations_reject_changed_identities_before_restore_or_cleanup(playbook, variable):
    play = yaml.safe_load((ROOT / "playbooks/operations/recovery" / playbook).read_text())[0]
    guard = next(
        condition
        for task in play["tasks"]
        for condition in task.get("ansible.builtin.assert", {}).get("that", [])
        if variable in condition
    )
    variables = {
        "recovery_original": {"resources": [{"metadata": {"uid": "expected"}}]},
        "recovery_backup": {"resources": [{"metadata": {"uid": "expected"}}]},
        "item": {"metadata": {"annotations": {"soyspray.vip/backup-uid": "expected"}}},
    }
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = [guard]
    assert condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
    for value in ("expected", "replacement"):
        supplied = {**variables, variable: value}
        assert condition.evaluate_conditional(
            Templar(loader=loader, variables=supplied), supplied
        ) is (value == "expected")


@pytest.mark.parametrize("failure", [None, "preflight", "restore", "data", "original", "cleanup"])
def test_restore_operation_cleans_up_after_failures_and_never_reports_partial_success(
    tmp_path, monkeypatch, capsys, failure
):
    import json
    import os
    import subprocess
    import sys

    from apps.boys import restore_check

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
    image = "ghcr.io/kpoxo6op/boys@sha256:" + "a" * 64
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
        "spec": {"replicas": 1, "strategy": {"type": "Recreate"}},
    }
    secret = {
        "metadata": {"uid": "secret-uid"},
        "data": {
            "pin": base64.b64encode(b"1357").decode(),
            "session-key": base64.b64encode(b"synthetic-identity-with-no-live-access").decode(),
        },
    }
    pod = {
        "metadata": {"name": "web"},
        "spec": {"containers": [{"name": "web", "image": image}]},
        "status": {"containerStatuses": [{"name": "web", "imageID": image, "ready": True}]},
    }
    operations = []
    volume_reads = 0

    def read(args, **kwargs):
        nonlocal volume_reads
        if args[:2] == ["git", "rev-parse"]:
            return "source-commit\n"
        if "view" in args:
            value = (
                {"contexts": []}
                if args[0] == "kubectl"
                else {
                    "boys_pin": "1357",
                    "boys_session_key": "synthetic-identity-with-no-live-access",
                }
            )
        else:
            config = Path(kwargs["env"]["KUBECONFIG"])
            assert config.stat().st_mode & 0o777 == 0o600
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
                value = {"items": [backup(point="2020-01-01T00:00:00Z")]}
            elif "secret" in args:
                value = secret
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
            variables = json.loads(args[-1])
            assert variables["recovery_expected_claim_uid"] == "claim-uid"
            assert variables["recovery_expected_backup_uid"] == "backup-uid"
            action = "cleanup" if "cleanup-restore.yml" in args[-3] else "restore"
            operations.append(action)
            if failure == action:
                raise subprocess.CalledProcessError(2, args)
        elif args[0] == sys.executable:
            assert (
                json.loads(kwargs["input"])["boys_session_key"]
                == "synthetic-identity-with-no-live-access"
            )
            return subprocess.CompletedProcess(
                args,
                2 if failure == "data" else 0,
                stdout=json.dumps({"data_checks": "failed" if failure == "data" else "passed"}),
            )
        else:
            assert args[:2] == ["kubectl", "cp"]
        return subprocess.CompletedProcess(args, 0)

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
    assert operations == ([] if failure == "preflight" else ["restore", "cleanup"])
    assert report["cleanup"] == (
        "not started"
        if failure == "preflight"
        else "failed - inspect the guarded cleanup log"
        if failure == "cleanup"
        else "completed"
    )
    assert not list(reports[0].parent.glob("working-*"))
    assert "synthetic-identity-with-no-live-access" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "messages,accepted",
    [
        (None, True),
        ({}, True),
        ({"Error": ""}, True),
        ({"Error": "failed"}, False),
        ({"error": "failed"}, False),
    ],
)
def test_native_restore_accepts_empty_longhorn_messages_and_rejects_errors(messages, accepted):
    play = yaml.safe_load((ROOT / "playbooks/operations/recovery/restore-volume.yml").read_text())[
        0
    ]
    guard = next(
        condition
        for task in play["tasks"]
        for condition in task.get("ansible.builtin.assert", {}).get("that", [])
        if "status.messages" in condition
    )
    variables = {"recovery_backup": {"resources": [{"status": {"messages": messages}}]}}
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = [guard]
    assert (
        condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
        is accepted
    )


@pytest.mark.parametrize(
    "field,value,accepted",
    [
        ("progress", 100, True),
        ("progress", 99, False),
        ("error", None, True),
        ("error", "", True),
        ("error", "failed", False),
    ],
)
def test_native_completion_and_error_guards_follow_longhorn_values(field, value, accepted):
    play = yaml.safe_load((ROOT / "playbooks/operations/recovery/restore-volume.yml").read_text())[
        0
    ]
    guard = next(
        condition
        for task in play["tasks"]
        for condition in task.get("ansible.builtin.assert", {}).get("that", [])
        if f"status.{field}" in condition
    )
    variables = {"recovery_backup": {"resources": [{"status": {field: value}}]}}
    loader = DataLoader()
    condition = Conditional(loader=loader)
    condition.when = [guard]
    assert (
        condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)
        is accepted
    )
