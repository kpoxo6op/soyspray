import json
import os
import subprocess

import pytest
import yaml
from conftest import ROOT

from scripts import ci_scope


@pytest.mark.parametrize(
    "path",
    [
        "kubernetes/boys/app/app.js",
        "apps/boys/argocd/application.yaml",
        "roles/apps/boys/tasks/enabled.yml",
    ],
)
def test_boys_changes_select_its_browser_checks(path):
    assert ci_scope.select([path]) == {"boys": True, "autism": False, "immich": False}


def test_shared_only_change_keeps_application_checks_optional():
    assert ci_scope.select(["scripts/backup_status.py", "tests/test_backup_status.py"]) == {
        "boys": False,
        "autism": False,
        "immich": False,
    }
    assert ci_scope.select(["apps/autism-traits/app/src/App.tsx"]) == {
        "boys": False,
        "autism": True,
        "immich": False,
    }


@pytest.mark.parametrize(
    "path",
    [
        "Makefile",
        ".github/workflows/ci.yml",
        "argocd/kustomization.yaml",
        "scripts/argo_preview.py",
        "scripts/app_command.py",
        "scripts/app_diff.py",
        "scripts/argocd_cli.py",
        "playbooks/bootstrap-apps.yml",
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
    old = tmp_path / "kubernetes/boys/old name.js"
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
    assert set(paths) == {"kubernetes/boys/old name.js", "apps/autism-traits/new.js"}
    assert ci_scope.select(paths) == {"boys": True, "autism": True, "immich": False}


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
    ],
)
def test_final_gate_rejects_failed_or_unexpectedly_skipped_jobs(failure):
    jobs = {
        "scope": {
            "result": "success",
            "outputs": {"boys": "true", "autism": "false", "immich": "false"},
        },
        "shared": {"result": "success"},
        "boys": {"result": "success"},
        "autism": {"result": "skipped"},
        "immich": {"result": "skipped"},
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
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    gate = workflow["jobs"]["check"]["steps"][0]["run"]
    run = subprocess.run(
        ["bash", "-e", "-c", gate],
        env={**os.environ, "RESULTS": json.dumps(jobs)},
        capture_output=True,
        text=True,
    )
    assert (run.returncode == 0) is (failure is None)


def test_immich_recovery_changes_select_native_image_checks():
    assert ci_scope.select(["apps/immich/backup/dump.sql"]) == {
        "boys": False,
        "autism": False,
        "immich": True,
    }
