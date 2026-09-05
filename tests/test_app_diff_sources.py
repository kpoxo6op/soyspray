import copy
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.app_diff_sources import pushed_sources, revision_arguments

ROOT = Path(__file__).resolve().parents[1]
APP = yaml.safe_load((ROOT / "apps/external-dns/argocd/application.yaml").read_text())
REPO = APP["spec"]["sources"][1]["repoURL"]
COMMIT = "a" * 40


def test_chart_and_git_positions_keep_chart_pin_and_use_exact_git_commit():
    live = copy.deepcopy(APP)
    live["spec"]["sources"][1]["targetRevision"] = "old-preview"
    original = copy.deepcopy(live)
    assert revision_arguments(live, APP, REPO, COMMIT) == [
        "--source-positions",
        "1",
        "--revisions",
        "1.14.0",
        "--source-positions",
        "2",
        "--revisions",
        COMMIT,
    ]
    assert live == original


def test_explicit_chart_upgrade_is_compared_at_its_new_version():
    desired = copy.deepcopy(APP)
    desired["spec"]["sources"][0]["targetRevision"] = "1.15.0"
    assert revision_arguments(APP, desired, REPO, COMMIT)[3] == "1.15.0"


@pytest.mark.parametrize(
    "change",
    [
        lambda spec: spec["sources"][0]["helm"].update(valueFiles=["$values/other.yaml"]),
        lambda spec: spec["sources"][0]["helm"].update(parameters=[{"name": "x", "value": "y"}]),
        lambda spec: spec["destination"].update(namespace="elsewhere"),
        lambda spec: spec.update(project="default"),
        lambda spec: spec["syncPolicy"]["automated"].update(prune=False),
        lambda spec: spec["sources"].reverse(),
        lambda spec: spec["sources"].pop(),
        lambda spec: spec["sources"][0].update(targetRevision="*"),
        lambda spec: spec["sources"][1].update(repoURL="https://example.com/foreign.git"),
        lambda spec: spec["sources"][1].update(targetRevision="other-branch"),
        lambda spec: spec["sources"][1].update(path="apps/extra"),
    ],
)
def test_unsupported_proposals_fail_before_native_comparison(change):
    desired = copy.deepcopy(APP)
    change(desired["spec"])
    with pytest.raises(ValueError):
        revision_arguments(APP, desired, REPO, COMMIT)


@pytest.mark.parametrize(
    "dirty,remote,declared,success",
    [
        (" M values.yaml", COMMIT, True, False),
        ("", "b" * 40, True, False),
        ("", COMMIT, False, False),
        ("", COMMIT, True, True),
    ],
)
def test_only_clean_exact_pushed_native_proposals_are_compared(
    tmp_path, monkeypatch, dirty, remote, declared, success
):
    bootstrap = tmp_path / "argocd/bootstrap/application.yaml"
    bootstrap.parent.mkdir(parents=True)
    bootstrap.write_text(yaml.safe_dump({"spec": {"source": {"repoURL": REPO}}}))
    calls = []

    def output(args, **kwargs):
        calls.append(args)
        if args[0] == "kubectl":
            return yaml.safe_dump(APP if declared else {"kind": "AppProject"})
        return {
            "status": dirty,
            "rev-parse": COMMIT,
            "symbolic-ref": "topic",
            "ls-remote": f"{remote}\trefs/heads/topic",
        }[args[1]]

    monkeypatch.setattr(subprocess, "check_output", output)
    if success:
        assert pushed_sources("external-dns", APP, tmp_path)[-1] == COMMIT
    else:
        with pytest.raises(ValueError):
            pushed_sources("external-dns", APP, tmp_path)
    if dirty or remote != COMMIT:
        assert not any(call[0] == "kubectl" for call in calls)
