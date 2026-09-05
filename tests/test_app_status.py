import copy
import importlib.util
import json
import subprocess

import pytest
from conftest import ROOT

spec = importlib.util.spec_from_file_location("app_status", ROOT / "scripts/app_status.py")
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


@pytest.fixture
def app():
    source = {
        "repoURL": "https://example.com/crew.git",
        "path": "apps/crew",
        "targetRevision": "HEAD",
    }
    destination = {"server": "https://kubernetes.default.svc", "namespace": "crew"}
    return {
        "kind": "Application",
        "metadata": {
            "name": "crew",
            "labels": {"soyspray.vip/owner": "platform"},
            "annotations": {
                "soyspray.vip/access-url": "https://crew.example.com",
                "soyspray.vip/access-method": "Personal PIN",
                "soyspray.vip/backup": "Longhorn critical",
            },
        },
        "spec": {"project": "crew", "source": source, "destination": destination},
        "status": {
            "sync": {
                "status": "Synced",
                "revision": "comparison-sha",
                "comparedTo": {"source": copy.deepcopy(source), "destination": destination},
            },
            "health": {"status": "Healthy"},
            "history": [
                {
                    "id": 1,
                    "deployedAt": "2026-09-05T00:00:00Z",
                    "source": source,
                    "revision": "last-sync-sha",
                }
            ],
            "operationState": {"phase": "Succeeded"},
        },
    }


def test_status_separates_desired_comparison_and_deployment_history(app):
    report = status.app_status(app)
    assert report["owner"] == {"value": "platform"}
    assert report["desired_sources"]["value"][0]["target_revision"] == {"value": "HEAD"}
    assert report["running_sources"]["value"][0]["resolved_revision"] == {"value": "comparison-sha"}
    assert report["last_successful_sync"]["value"]["sources"][0]["resolved_revision"] == {
        "value": "last-sync-sha"
    }
    assert report["access"]["urls"] == {"value": ["https://crew.example.com"]}
    assert report["access"]["verified"]["value"] == "unknown"
    assert report["recovery"]["declared_policy"]["value"] == "Longhorn critical"
    assert report["recovery"]["latest_backup"]["value"] == "unknown"
    assert report["recovery"]["last_restore"]["value"] == "unknown"


@pytest.mark.parametrize(
    "change", ["drift", "source", "destination", "running", "missing-revision"]
)
def test_unconfirmed_or_partial_sync_does_not_claim_a_running_revision(app, change):
    if change == "drift":
        app["status"]["sync"]["status"] = "OutOfSync"
        app["status"]["operationState"]["phase"] = "Failed"
    elif change == "source":
        app["spec"]["source"]["targetRevision"] = "next-branch"
    elif change == "destination":
        app["status"]["sync"]["comparedTo"]["destination"] = {"namespace": "old"}
    elif change == "running":
        app["status"]["operationState"]["phase"] = "Running"
    else:
        del app["status"]["sync"]["revision"]
    report = status.app_status(app)
    assert report["running_sources"]["value"] == "unknown"
    assert report["running_sources"]["cause"]
    assert report["last_successful_sync"]["value"]["sources"][0]["resolved_revision"]["value"] == (
        "last-sync-sha"
    )


def test_multisource_revisions_keep_chart_and_git_identity_without_values(app):
    chart = {
        "repoURL": "https://charts.example.com",
        "chart": "viewer",
        "targetRevision": "1.0.0",
        "helm": {"parameters": [{"name": "credential", "value": "must-not-be-printed"}]},
    }
    git = app["spec"].pop("source")
    app["spec"]["sources"] = [chart, git]
    app["status"]["sync"]["comparedTo"] = copy.deepcopy(app["spec"])
    app["status"]["sync"]["revisions"] = ["1.0.0", "values-sha"]
    report = status.app_status(app)
    running = report["running_sources"]["value"]
    assert [source["resolved_revision"]["value"] for source in running] == ["1.0.0", "values-sha"]
    assert "must-not-be-printed" not in json.dumps(report)
    app["status"]["sync"]["revisions"] = ["1.0.0"]
    assert status.app_status(app)["running_sources"]["value"] == "unknown"


def test_missing_metadata_and_observations_remain_unknown_with_causes():
    report = status.app_status({"metadata": {"name": "new-app"}, "spec": {}})
    for field in (
        "owner",
        "project",
        "namespace",
        "health",
        "sync",
        "desired_sources",
        "comparison_sources",
        "running_sources",
        "last_successful_sync",
        "reconciled_at",
    ):
        assert report[field]["value"] == "unknown"
        assert report[field]["cause"]


def test_inventory_comes_from_application_metadata(tmp_path, capsys, app):
    other = copy.deepcopy(app)
    other["metadata"]["name"] = "another-app"
    other["metadata"]["labels"] = {}
    saved = tmp_path / "applications.json"
    saved.write_text(json.dumps({"kind": "List", "items": [app, other]}))
    assert status.main(["apps", "--format", "json", "--input", str(saved)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [item["name"] for item in report["applications"]] == ["another-app", "crew"]
    assert report["applications"][0]["owner"]["value"] == "unknown"
    assert (
        status.main(["status", "--app", "absent", "--format", "json", "--input", str(saved)]) == 2
    )
    assert (
        "no Application named absent"
        in json.loads(capsys.readouterr().out)["applications"]["cause"]
    )


@pytest.mark.parametrize("failure", ["unavailable", "timeout", "invalid-json"])
def test_failed_inventory_read_is_an_error_with_unknown_status(monkeypatch, capsys, failure):
    def fake_run(command, **kwargs):
        assert command == [
            "kubectl",
            "--request-timeout=10s",
            "-n",
            "argocd",
            "get",
            "applications",
            "-o",
            "json",
        ]
        assert kwargs["timeout"] == 20
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 20)
        return subprocess.CompletedProcess(
            command,
            1 if failure == "unavailable" else 0,
            stdout="not-json",
            stderr="The API is unavailable",
        )

    monkeypatch.setattr(status.subprocess, "run", fake_run)
    assert status.main(["status", "--app", "crew", "--format", "json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["applications"]["value"] == "unknown"
    assert report["applications"]["cause"]


def test_offline_status_keeps_app_health_when_backup_input_fails(
    tmp_path, capsys, app, monkeypatch
):
    from scripts.restore_evidence import Path as EvidencePath

    app["metadata"]["annotations"]["soyspray.vip/data-claims"] = "crew/data"
    saved = tmp_path / "applications.json"
    saved.write_text(json.dumps({"kind": "List", "items": [app]}))
    bad = tmp_path / "backups.json"
    bad.write_text("invalid JSON")

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline status must not query the cluster or scan private reports")

    monkeypatch.setattr(status.subprocess, "run", forbidden)
    monkeypatch.setattr(EvidencePath, "glob", forbidden)
    assert (
        status.main(
            [
                "status",
                "--app",
                "crew",
                "--input",
                str(saved),
                "--backup-input",
                str(bad),
                "--format",
                "json",
            ]
        )
        == 2
    )
    report = json.loads(capsys.readouterr().out)
    row = report["applications"][0]
    assert row["health"]["value"] == "Healthy"
    assert row["recovery"]["last_restore"]["value"][0]["evidence"]["value"] == "unknown"
    assert row["recovery"]["latest_backup"]["value"][0]["backup"]["value"] == "unknown"
