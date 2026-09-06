import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from scripts import restore_schedule


@pytest.fixture(autouse=True)
def fixed_revision(monkeypatch):
    monkeypatch.setattr(restore_schedule, "revision", lambda root: "checked-revision")


def fake_runner(state_home, calls, failures=None):
    failures = failures or {}

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["XDG_STATE_HOME"] == str(state_home)
        if "full-check" in command:
            return subprocess.CompletedProcess(command, 0, stdout="gate\n", stderr="")
        app = command[-1].split("=", 1)[1]
        status, cleanup, returncode = failures.get(app, ("passed", "completed", 0))
        check_id = f"check-{app}"
        report = {
            "schema_version": 1,
            "app": app,
            "check_id": check_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "cleanup": cleanup,
        }
        path = state_home / "soyspray/restores" / app / check_id / "report.json"
        path.parent.mkdir(mode=0o700, parents=True)
        path.write_text(json.dumps(report))
        return subprocess.CompletedProcess(
            command, returncode, stdout=json.dumps(report), stderr=""
        )

    return run


def read_schedule_report(state_home):
    reports = list((state_home / "soyspray/restores/schedule").glob("*/report.json"))
    assert len(reports) == 1
    return json.loads(reports[0].read_text())


def test_schedule_runs_gate_and_all_apps_in_order(tmp_path):
    calls = []
    report, code = restore_schedule.run_schedule(
        tmp_path / "repo", tmp_path, fake_runner(tmp_path, calls)
    )

    assert code == 0
    assert calls == [
        ["make", "--no-print-directory", "full-check"],
        ["make", "--no-print-directory", "-o", "check", "restore-check", "APP=boys"],
        ["make", "--no-print-directory", "-o", "check", "restore-check", "APP=vaultwarden"],
        ["make", "--no-print-directory", "-o", "check", "restore-check", "APP=obsidian-livesync"],
    ]
    assert report["status"] == "passed"
    assert [item["app"] for item in report["apps"]] == list(restore_schedule.APPS)
    assert len({item["run_id"] for item in report["apps"]}) == 1
    assert read_schedule_report(tmp_path)["status"] == "passed"


def test_schedule_continues_after_failed_app_with_completed_cleanup(tmp_path):
    calls = []
    report, code = restore_schedule.run_schedule(
        tmp_path / "repo",
        tmp_path,
        fake_runner(tmp_path, calls, {"boys": ("failed", "completed", 2)}),
    )

    assert code == 2
    assert report["status"] == "failed"
    assert len(report["apps"]) == 3
    assert calls[-1][-1] == "APP=obsidian-livesync"
    assert report["apps"][0]["cleanup"] == "completed"


def test_schedule_stops_when_cleanup_evidence_is_missing(tmp_path):
    calls = []
    report, code = restore_schedule.run_schedule(
        tmp_path / "repo",
        tmp_path,
        fake_runner(tmp_path, calls, {"boys": ("failed", "pending", 2)}),
    )

    assert code == 2
    assert report["status"] == "failed"
    assert len(report["apps"]) == 1
    assert calls == [
        ["make", "--no-print-directory", "full-check"],
        ["make", "--no-print-directory", "-o", "check", "restore-check", "APP=boys"],
    ]


def test_schedule_stops_before_apps_when_shared_gate_fails(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["XDG_STATE_HOME"] == str(tmp_path)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    report, code = restore_schedule.run_schedule(tmp_path / "repo", tmp_path, run)

    assert code == 2
    assert report["status"] == "failed"
    assert report["apps"] == []
    assert calls == [["make", "--no-print-directory", "full-check"]]


def test_schedule_units_are_user_scoped_and_monthly():
    recovery = Path("playbooks/operations/recovery")
    timer = (recovery / "systemd/soyspray-restore-check.timer.j2").read_text()
    service = (recovery / "systemd/soyspray-restore-check.service.j2").read_text()
    play = yaml.safe_load((recovery / "install-restore-check-schedule.yml").read_text())[0]

    assert "OnCalendar=*-*-01 03:00:00" in timer
    assert "Persistent=true" in timer
    assert "-m scripts.restore_schedule" in service
    assert play["hosts"] == "localhost"
    assert play["connection"] == "local"
    assert play["become"] is False
    systemd_tasks = [
        task["ansible.builtin.systemd_service"]
        for task in play["tasks"]
        if "ansible.builtin.systemd_service" in task
    ]
    assert all(task.get("scope") == "user" for task in systemd_tasks)
    assert any(task.get("name") == "soyspray-restore-check.timer" for task in systemd_tasks)


def test_schedule_stops_if_revision_changes_after_gate(tmp_path, monkeypatch):
    revisions = iter(["before", "after"])
    monkeypatch.setattr(restore_schedule, "revision", lambda root: next(revisions))
    calls = []
    report, code = restore_schedule.run_schedule(
        tmp_path / "repo", tmp_path, fake_runner(tmp_path, calls)
    )
    assert code == 2
    assert report["apps"] == []
    assert len(calls) == 1
    assert report["finished_at"]


def test_schedule_records_interruption_and_allows_guarded_cleanup(tmp_path):
    def interrupted(command, **kwargs):
        assert kwargs["termination_grace"] == 900
        raise restore_schedule.RestoreInterrupted

    with pytest.raises(restore_schedule.RestoreInterrupted):
        restore_schedule.run_schedule(tmp_path / "repo", tmp_path, interrupted)
    report = read_schedule_report(tmp_path)
    assert report["status"] == "failed"
    assert report["finished_at"]
