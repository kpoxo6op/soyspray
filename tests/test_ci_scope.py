import json
import os
import subprocess

import pytest
import yaml
from conftest import ROOT

from scripts import ci_scope


def selected(**apps):
    """Every application boundary, with only the named ones selected."""
    return {name: apps.get(name, False) for name in (*ci_scope.APP_PATHS, "autism", "boys")}


@pytest.mark.parametrize(
    "path",
    [
        "apps/boys/app/app.js",
        "apps/boys/argocd/application.yaml",
        "apps/boys/bootstrap-tasks.yml",
    ],
)
def test_boys_changes_select_its_browser_checks(path):
    assert ci_scope.select([path]) == selected(boys=True)


def test_shared_only_change_keeps_application_checks_optional():
    assert (
        ci_scope.select(["scripts/backup_status.py", "tests/test_backup_status.py"]) == selected()
    )
    assert ci_scope.select(["apps/autism-traits/app/src/App.tsx"]) == selected(autism=True)


@pytest.mark.parametrize(
    "path",
    [
        "Makefile",
        ".github/workflows/ci.yml",
        "argocd/kustomization.yaml",
        "scripts/app_command.py",
        "scripts/app_diff.py",
        "scripts/app_diff_sources.py",
        "scripts/argocd_cli.py",
        "playbooks/bootstrap-apps.yml",
        "playbooks/bootstrap-app-inputs.yml",
        "playbooks/operations/recovery/restore-volume.yml",
        "playbooks/operations/recovery/cleanup-restore.yml",
    ],
)
def test_shared_deployment_controls_and_full_checks_select_all_apps(path):
    assert all(ci_scope.select([path]).values())
    assert all(ci_scope.select([], full=True).values())


def test_missing_base_is_reported_for_a_full_fallback(monkeypatch):
    assert ci_scope.changed_paths(None) is None

    def unavailable(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(ci_scope.subprocess, "run", unavailable)
    assert ci_scope.changed_paths("unavailable-commit") is None


def test_deleted_and_renamed_paths_are_both_checked(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "--quiet")
    old = tmp_path / "apps/boys/old name.js"
    old.parent.mkdir(parents=True)
    old.write_text("source")
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.test",
        "commit",
        "--no-gpg-sign",
        "-qm",
        "Initial fixture",
    )
    base = git("rev-parse", "HEAD")
    new = tmp_path / "apps/autism-traits/new.js"
    new.parent.mkdir(parents=True)
    old.rename(new)
    git("add", "-A")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.test",
        "commit",
        "--no-gpg-sign",
        "-qm",
        "Move fixture",
    )
    monkeypatch.chdir(tmp_path)
    paths = ci_scope.changed_paths(base)
    assert set(paths) == {"apps/boys/old name.js", "apps/autism-traits/new.js"}
    assert ci_scope.select(paths) == selected(boys=True, autism=True)


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "shared",
        "scope",
        "selected-skipped",
        "unselected-failed",
        "missing-output",
        "cancelled",
        "domain-image-failed",
        "media-image-failed",
        "diagnosis-image-failed",
    ],
)
def test_final_gate_rejects_failed_or_unexpectedly_skipped_jobs(failure):
    jobs = {
        "scope": {
            "result": "success",
            "outputs": {
                "boys": "true",
                "autism": "false",
                "immich": "false",
                "domain_health": "false",
                "media_helper": "false",
                "gi": "false",
                "cluster_diagnosis": "false",
            },
        },
        "shared": {"result": "success"},
        "boys": {"result": "success"},
        "autism": {"result": "skipped"},
        "immich": {"result": "skipped"},
        "domain_health": {"result": "skipped"},
        "media_helper": {"result": "skipped"},
        "gi": {"result": "skipped"},
        "cluster_diagnosis": {"result": "skipped"},
    }
    if failure in {"shared", "scope"}:
        jobs[failure]["result"] = "failure"
    elif failure == "selected-skipped":
        jobs["boys"]["result"] = "skipped"
    elif failure == "unselected-failed":
        jobs["autism"]["result"] = "failure"
    elif failure == "missing-output":
        jobs["scope"]["outputs"].pop("boys")
    elif failure == "cancelled":
        jobs["boys"]["result"] = "cancelled"
    elif failure == "domain-image-failed":
        jobs["scope"]["outputs"]["domain_health"] = "true"
        jobs["domain_health"]["result"] = "failure"
    elif failure == "media-image-failed":
        jobs["scope"]["outputs"]["media_helper"] = "true"
        jobs["media_helper"]["result"] = "failure"
    elif failure == "diagnosis-image-failed":
        jobs["scope"]["outputs"]["cluster_diagnosis"] = "true"
        jobs["cluster_diagnosis"]["result"] = "failure"
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    gate = workflow["jobs"]["check"]["steps"][0]["run"]
    run = subprocess.run(
        ["bash", "-e", "-c", gate],
        env={**os.environ, "RESULTS": json.dumps(jobs)},
        capture_output=True,
        text=True,
    )
    assert (run.returncode == 0) is (failure is None)


@pytest.mark.parametrize(
    "path",
    [
        "apps/gi/manifests/deployment.yaml",
        "apps/gi/argocd/application.yaml",
        "apps/gi/bootstrap-tasks.yml",
        "apps/gi/tests/test_gi_boundary.py",
    ],
)
def test_gi_changes_select_its_boundary_checks(path):
    assert ci_scope.select([path]) == selected(gi=True)


def test_immich_recovery_changes_select_native_image_checks():
    assert ci_scope.select(["apps/immich-offsite-backup/manifests/runtime/dump.sql"]) == selected(
        immich=True
    )


def test_domain_health_changes_select_the_native_image_checks():
    assert ci_scope.select(["apps/domain-health/app/domain-health-exporter.py"]) == selected(
        domain_health=True
    )


@pytest.mark.parametrize(
    "path",
    [
        "apps/media-helper/app/app.py",
        "apps/media-helper/app/channels.json",
        "tests/test_live_tv.py",
    ],
)
def test_helper_source_catalog_and_consumer_checks_select_its_image(path):
    selected = ci_scope.select([path])
    assert selected.pop("media_helper") is True
    assert not any(selected.values())
