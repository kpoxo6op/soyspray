import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts.app_recovery import app_recovery
from scripts.restore_evidence import read_evidence

NOW = datetime(2026, 9, 6, 0, tzinfo=timezone.utc)
IMAGE = "ghcr.io/example/boys@sha256:" + "a" * 64


@pytest.fixture
def record():
    return {
        "schema_version": 1,
        "app": "boys",
        "check_id": "check-1",
        "started_at": (NOW - timedelta(hours=2)).isoformat(),
        "finished_at": (NOW - timedelta(hours=1)).isoformat(),
        "status": "passed",
        "cleanup": "completed",
        "source_claim_uid": "claim-1",
        "source_volume_uid": "pv-1",
        "image": IMAGE,
        "backup": {"recovery_point": (NOW - timedelta(hours=3)).isoformat()},
        "original_resources": "unchanged",
        "data": {"data_checks": "passed", "private_note": "never-output-this"},
        "cause": "never-output-this",
    }


def save(root, record):
    path = root / "boys" / record["check_id"] / "report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    return path


def read(root):
    return read_evidence("boys", "claim-1", "pv-1", NOW, root)


def test_success_reports_age_and_identity_without_private_content(tmp_path, record):
    save(tmp_path, record)
    evidence = read(tmp_path)["value"]
    success = evidence["last_success"]["value"]
    assert success["accepted"] is True
    assert success["age_seconds"] == 3600
    assert success["image"] == IMAGE
    assert success["matches_observed_claim_and_pv"] is True
    assert success["human_personal_pin"]["value"] == "unknown"
    assert "never-output-this" not in json.dumps(evidence)


@pytest.mark.parametrize(
    "change",
    [
        {"status": "running", "finished_at": None},
        {"status": "failed"},
        {"cleanup": "pending"},
        {"original_resources": "changed"},
        {"source_claim_uid": "recreated-claim"},
        {"source_volume_uid": "recreated-pv"},
        {"data": {"data_checks": "failed"}},
        {"backup": {"recovery_point": "no-time"}},
        {"backup": {"recovery_point": (NOW + timedelta(hours=1)).isoformat()}},
        {"image": "mutable:latest"},
    ],
)
def test_incomplete_or_wrong_identity_checks_cannot_prove_restore(tmp_path, record, change):
    save(tmp_path, {**record, **change})
    value = read(tmp_path)["value"]
    assert value["last_success"]["value"] == "unknown"
    assert value["last_attempt"]["value"]["accepted"] is False


def test_later_failure_does_not_hide_previous_success_or_its_age(tmp_path, record):
    save(tmp_path, record)
    later = {
        **record,
        "check_id": "check-2",
        "status": "failed",
        "started_at": (NOW - timedelta(minutes=30)).isoformat(),
        "finished_at": (NOW - timedelta(minutes=20)).isoformat(),
    }
    save(tmp_path, later)
    value = read(tmp_path)["value"]
    assert value["last_attempt"]["value"]["status"] == "failed"
    assert value["last_success"]["value"]["check_id"] == "check-1"
    assert value["last_success"]["value"]["age_seconds"] == 3600


@pytest.mark.parametrize(
    "change",
    [
        {"app": "another-app"},
        {"schema_version": 2},
        {"data": "bad"},
        {"image": []},
        {"finished_at": "2020-01-01"},
        {"started_at": (NOW + timedelta(hours=1)).isoformat()},
    ],
)
def test_invalid_records_make_latest_attempt_unknown(tmp_path, record, change):
    save(tmp_path, {**record, **change})
    value = read(tmp_path)["value"]
    assert value["last_attempt"]["value"] == "unknown"
    assert value["invalid_reports"] == 1
    assert value["last_success"]["value"] == "unknown"


def test_corrupt_report_does_not_hide_an_older_valid_success(tmp_path, record):
    save(tmp_path, record)
    path = tmp_path / "boys" / "later" / "report.json"
    path.parent.mkdir()
    path.write_text("not JSON")
    value = read(tmp_path)["value"]
    assert value["last_attempt"]["value"] == "unknown"
    assert value["last_success"]["value"]["accepted"] is True


def test_missing_evidence_and_unverified_binding_are_unknown(tmp_path):
    assert read(tmp_path)["value"] == "unknown"
    assert read_evidence("boys", None, "pv-1", NOW, tmp_path)["value"] == "unknown"
    assert read_evidence("../boys", "claim-1", "pv-1", NOW, tmp_path)["value"] == "unknown"


def test_report_links_are_not_followed(tmp_path, record):
    path = save(tmp_path, record)
    data = path.read_text()
    path.unlink()
    target = tmp_path / "elsewhere.json"
    target.write_text(data)
    path.symlink_to(target)
    assert read(tmp_path)["value"]["last_success"]["value"] == "unknown"


def test_app_inventory_controls_mapping_and_offline_reads(tmp_path, record):
    save(tmp_path, record)
    app = {"metadata": {"name": "boys", "annotations": {"soyspray.vip/data-claims": "boys/data"}}}
    backup = {
        "longhorn": {
            "value": {
                "claims": [
                    {
                        "claim": "boys/data",
                        "claim_uid": "claim-1",
                        "pv_uid": "pv-1",
                        "backup": {"value": {"name": "snapshot"}},
                    }
                ]
            }
        }
    }
    result = app_recovery(app, backup, NOW, tmp_path)
    assert result["latest_backup"]["value"][0]["backup"]["value"]["name"] == "snapshot"
    assert result["last_restore"]["value"][0]["evidence"]["value"]["last_success"]["value"][
        "accepted"
    ]
    offline = app_recovery(app, backup, NOW, tmp_path, read_private=False)
    assert offline["last_restore"]["value"][0]["evidence"]["value"] == "unknown"
    missing = copy.deepcopy(app)
    missing["metadata"]["annotations"] = {}
    assert app_recovery(missing, backup, NOW, tmp_path)["last_restore"]["value"] == "unknown"
    backup["longhorn"] = {"value": "unknown", "cause": "API unavailable"}
    assert (
        app_recovery(app, backup, NOW, tmp_path)["last_restore"]["value"][0]["evidence"]["value"]
        == "unknown"
    )
