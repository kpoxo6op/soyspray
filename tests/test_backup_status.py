import copy
import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from scripts import backup_status as status

NOW = datetime(2026, 9, 5, 7, tzinfo=timezone.utc)


@pytest.fixture
def data():
    result = {key: {"items": []} for key in status.RESOURCES}
    result["claims"]["items"] = [
        {
            "metadata": {"name": "data", "namespace": "notes", "uid": "claim-uid"},
            "spec": {"volumeName": "pv-name"},
            "status": {"phase": "Bound"},
        }
    ]
    result["pvs"]["items"] = [
        {
            "metadata": {"name": "pv-name"},
            "spec": {
                "claimRef": {"uid": "claim-uid"},
                "csi": {"driver": "driver.longhorn.io", "volumeHandle": "volume-1"},
            },
        }
    ]
    result["volumes"]["items"] = [
        {
            "metadata": {
                "name": "volume-1",
                "labels": {"recurring-job-group.longhorn.io/critical": "enabled"},
            },
            "spec": {"backupTargetName": "offsite", "numberOfReplicas": 3},
            "status": {"robustness": "healthy"},
        }
    ]
    result["longhorn_jobs"]["items"] = [
        {
            "metadata": {"name": "recent"},
            "spec": {
                "task": "backup-force-create",
                "groups": ["critical"],
                "cron": "*/30 * * * *",
                "retain": 48,
            },
        },
        {
            "metadata": {"name": "local-snapshot"},
            "spec": {"task": "snapshot", "groups": ["critical"]},
        },
    ]
    result["targets"]["items"] = [
        {
            "metadata": {"name": "offsite"},
            "status": {"available": True, "lastSyncedAt": "2026-09-05T06:59:00Z"},
        }
    ]
    result["longhorn_backups"]["items"] = [
        {
            "metadata": {
                "name": "good",
                "labels": {"backup-volume": "volume-1", "backup-target": "offsite"},
            },
            "status": {
                "volumeName": "volume-1",
                "backupTargetName": "offsite",
                "state": "Completed",
                "progress": 100,
                "snapshotCreatedAt": "2026-09-05T06:30:00Z",
                "backupCreatedAt": "2026-09-05T06:59:00Z",
            },
        }
    ]
    result["clusters"]["items"] = [
        {
            "metadata": {"name": "database", "namespace": "photos"},
            "spec": {},
            "status": {"conditions": [{"type": "ContinuousArchiving", "status": "True"}]},
        }
    ]
    result["cnpg_backups"]["items"] = [
        {
            "metadata": {"name": "base", "namespace": "photos"},
            "spec": {"cluster": {"name": "database"}},
            "status": {
                "phase": "completed",
                "startedAt": "2026-09-05T03:00:00Z",
                "stoppedAt": "2026-09-05T06:00:00Z",
                "method": "barmanObjectStore",
            },
        }
    ]
    return result


def test_backup_age_uses_snapshot_time_and_schedules_do_not_prove_success(data):
    report = status.longhorn_report(data, NOW)["value"]
    assert report["bound_claims"] == 1
    assert report["claims_with_backup_schedule"] == 1
    row = report["claims"][0]
    assert [job["name"] for job in row["backup_schedules"]] == ["recent"]
    assert row["backup"]["value"]["age_seconds"] == {"value": 1800}
    data["longhorn_backups"]["items"] = []
    report = status.longhorn_report(data, NOW)["value"]
    assert report["claims_with_backup_schedule"] == 1
    assert report["claims_with_completed_backup"] == 0
    assert report["claims"][0]["backup"]["cause"]


@pytest.mark.parametrize(
    "invalid", ["pending", "failed", "partial", "error", "wrong-target", "no-time"]
)
def test_newer_incomplete_or_wrong_target_backup_cannot_replace_success(data, invalid):
    new = copy.deepcopy(data["longhorn_backups"]["items"][0])
    new["metadata"]["name"] = "newer"
    new["status"]["snapshotCreatedAt"] = "2026-09-05T06:50:00Z"
    if invalid == "pending":
        new.pop("status")
    elif invalid == "failed":
        new["status"] = {"state": "Error"}
    elif invalid == "partial":
        new["status"]["progress"] = 80
    elif invalid == "error":
        new["status"]["messages"] = {"Error": "failed to finish"}
    elif invalid == "wrong-target":
        new["status"]["backupTargetName"] = "retired-target"
    else:
        new["status"].pop("snapshotCreatedAt")
    data["longhorn_backups"]["items"].append(new)
    row = status.longhorn_report(data, NOW)["value"]["claims"][0]
    assert row["backup"]["value"]["name"] == "good"
    if invalid in {"failed", "error"}:
        assert row["failed_backups"] == ["newer"]
    if invalid == "pending":
        assert row["unfinished_backups"] == ["newer"]


def test_deleted_claims_are_not_covered_and_unavailable_targets_stay_visible(data):
    retired = copy.deepcopy(data["claims"]["items"][0])
    retired["metadata"].update(name="retired", deletionTimestamp="2026-09-05T06:00:00Z")
    data["claims"]["items"].append(retired)
    data["targets"]["items"][0]["status"]["available"] = False
    report = status.longhorn_report(data, NOW)["value"]
    assert report["bound_claims"] == 1
    assert report["claims"][0]["target_available"] == {"value": False}


def test_a_replaced_claim_cannot_inherit_another_claims_backup(data):
    data["pvs"]["items"][0]["spec"]["claimRef"]["uid"] = "other-claim-uid"
    row = status.longhorn_report(data, NOW)["value"]["claims"][0]
    assert row["backup"]["value"] == "unknown"
    assert "PVC UID" in row["backup"]["cause"]


def test_base_backup_time_is_separate_from_wal_age_and_namespace_identity(data):
    foreign = copy.deepcopy(data["cnpg_backups"]["items"][0])
    foreign["metadata"]["namespace"] = "other"
    foreign["status"]["startedAt"] = "2026-09-05T06:50:00Z"
    data["cnpg_backups"]["items"].append(foreign)
    report = status.cnpg_report(data, NOW)["value"][0]
    assert report["base_backup"]["value"]["age_seconds"] == {"value": 14400}
    assert report["continuous_archiving"] == {"value": "True"}
    assert report["latest_wal_age_seconds"]["value"] == "unknown"
    assert report["latest_wal_age_seconds"]["cause"]


@pytest.mark.parametrize("value", [None, "bad", "2026-09-05T06:00:00", "2026-09-05T07:00:00.1Z"])
def test_invalid_or_future_timestamps_do_not_claim_a_fresh_backup(value):
    assert status.age(value, NOW)["value"] == "unknown"
    assert status.age((NOW - timedelta(seconds=1)).isoformat(), NOW) == {"value": 1}


def test_failed_source_keeps_other_observations_but_returns_nonzero(data, tmp_path, capsys):
    data["longhorn_backups"] = status.unknown("API unavailable")
    report = status.build_report(data, NOW)
    assert report["longhorn"]["value"] == "unknown"
    assert "API unavailable" in report["longhorn"]["cause"]
    assert len(report["cnpg"]["value"]) == 1
    for key in ("restic", "restore_evidence", "seven_day_rpo"):
        assert report[key]["value"] == "unknown"
    saved = tmp_path / "observations.json"
    saved.write_text(json.dumps(data))
    assert status.main(["--input", str(saved), "--format", "json"]) == 2
    assert json.loads(capsys.readouterr().out)["longhorn"]["value"] == "unknown"


def test_api_errors_preserve_the_failure_cause_without_reading_secrets(monkeypatch):
    def fake_run(command, **kwargs):
        assert command[:4] == ["kubectl", "--request-timeout=10s", "get", "backups.longhorn.io"]
        assert kwargs["timeout"] == 20
        raise subprocess.CalledProcessError(1, command, stderr="Forbidden: cannot list backups")

    monkeypatch.setattr(status.subprocess, "run", fake_run)
    key, value = status.read_resource(("longhorn_backups", status.RESOURCES["longhorn_backups"]))
    assert key == "longhorn_backups"
    assert value["value"] == "unknown"
    assert "Forbidden" in value["cause"]


def test_private_restore_reports_attach_only_through_application_metadata(data, tmp_path):
    data["pvs"]["items"][0]["metadata"]["uid"] = "pv-uid"
    data["applications"]["items"] = [
        {
            "metadata": {
                "name": "boys",
                "namespace": "argocd",
                "annotations": {"soyspray.vip/data-claims": "notes/data"},
            }
        }
    ]
    path = tmp_path / "boys" / "check-1" / "report.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "app": "boys",
                "check_id": "check-1",
                "started_at": "2026-09-05T04:00:00Z",
                "finished_at": "2026-09-05T05:00:00Z",
                "status": "passed",
                "cleanup": "completed",
                "original_resources": "unchanged",
                "source_claim_uid": "claim-uid",
                "source_volume_uid": "pv-uid",
                "image": "ghcr.io/example/boys@sha256:" + "a" * 64,
                "backup": {"recovery_point": "2026-09-05T03:30:00Z"},
                "data": {"data_checks": "passed"},
            }
        )
    )
    report = status.build_report(data, NOW)
    status.attach_restore_evidence(report, data, NOW, tmp_path)
    evidence = report["restore_evidence"]["value"][0]["claims"]["value"][0]["evidence"]["value"]
    assert evidence["last_success"]["value"]["age_seconds"] == 7200
    data["pvs"]["items"][0]["metadata"]["uid"] = "replacement-pv"
    report = status.build_report(data, NOW)
    status.attach_restore_evidence(report, data, NOW, tmp_path)
    evidence = report["restore_evidence"]["value"][0]["claims"]["value"][0]["evidence"]["value"]
    assert evidence["last_success"]["value"] == "unknown"
    data["applications"] = {"value": "unknown", "cause": "API unavailable"}
    status.attach_restore_evidence(report, data, NOW, tmp_path)
    assert report["restore_evidence"]["value"] == "unknown"


def test_native_unknown_volume_health_keeps_the_source_cause(data):
    data["volumes"]["items"][0]["status"]["robustness"] = "unknown"
    health = status.longhorn_report(data, NOW)["value"]["claims"][0]["volume_health"]
    assert health == {"value": "unknown", "cause": "Longhorn reports volume health as unknown."}
