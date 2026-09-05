import copy
import json
import subprocess

import pytest
import yaml
from conftest import load_yaml

from scripts.argo_preview import prepare


def child(name, sources):
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {"name": name, "namespace": "argocd"},
        "spec": {"sources": sources},
    }


def test_native_patch_changes_only_the_selected_apps_repo_sources(tmp_path):
    root = load_yaml("argocd/bootstrap/application.yaml")
    repo = root["spec"]["source"]["repoURL"]
    selected = child(
        "app.a",
        [
            {
                "repoURL": "https://charts.example.test",
                "chart": "upstream",
                "targetRevision": "1.2.3",
            },
            {"repoURL": repo, "ref": "values", "targetRevision": "HEAD"},
            {"repoURL": repo, "path": "apps/example/config"},
            {"repoURL": "https://github.com/other/repo", "path": ".", "targetRevision": "main"},
        ],
    )
    other = child("app-a", [{"repoURL": repo, "path": "apps/other", "targetRevision": "HEAD"}])
    original = copy.deepcopy([selected, other])
    prepared = prepare(root, original, "codex/app-preview", "app.a")
    (tmp_path / "objects.yaml").write_text(yaml.safe_dump_all(original))
    (tmp_path / "kustomization.yaml").write_text(
        yaml.safe_dump(
            {
                "apiVersion": "kustomize.config.k8s.io/v1beta1",
                "kind": "Kustomization",
                "resources": ["objects.yaml"],
                "patches": prepared["spec"]["source"]["kustomize"]["patches"],
            }
        )
    )
    rendered = list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(tmp_path)], text=True)
        )
    )
    by_name = {app["metadata"]["name"]: app for app in rendered}
    expected = copy.deepcopy(selected)
    for index in (1, 2):
        expected["spec"]["sources"][index]["targetRevision"] = "codex/app-preview"
    assert by_name["app.a"] == expected
    assert by_name["app-a"] == other
    assert original == [selected, other]
    assert prepared["spec"]["syncPolicy"] == root["spec"]["syncPolicy"]
    assert prepared["metadata"] == root["metadata"]


def test_single_source_preview_uses_the_native_single_source_path():
    root = load_yaml("argocd/bootstrap/application.yaml")
    app = child("single", [])
    app["spec"] = {"source": {"repoURL": root["spec"]["source"]["repoURL"], "path": "apps/single"}}
    prepared = prepare(root, [app], "codex/preview", "single")
    patch = prepared["spec"]["source"]["kustomize"]["patches"][0]["patch"]
    assert json.loads(patch) == [
        {"op": "add", "path": "/spec/source/targetRevision", "value": "codex/preview"}
    ]


def test_head_handoff_has_no_preview_parameters_and_preserves_lifecycle_controls():
    root = load_yaml("argocd/bootstrap/application.yaml")
    prepared = prepare(root, [], "HEAD")
    assert prepared == root
    assert "kustomize" not in prepared["spec"]["source"]
    assert prepared["spec"]["syncPolicy"]["automated"]["prune"] is False
    assert not prepared["metadata"].get("finalizers")


def test_chart_only_apps_keep_their_pinned_upstream_version():
    root = load_yaml("argocd/bootstrap/application.yaml")
    app = child(
        "chart",
        [
            {
                "repoURL": "https://charts.example.test",
                "chart": "upstream",
                "targetRevision": "1.2.3",
            }
        ],
    )
    prepared = prepare(root, [app], "codex/chart-change", "chart")
    assert prepared["spec"]["source"] == {
        **root["spec"]["source"],
        "targetRevision": "codex/chart-change",
    }


@pytest.mark.parametrize("case", ["unknown", "duplicate", "ambiguous", "head"])
def test_invalid_selection_fails_before_any_root_definition_is_changed(case):
    root = load_yaml("argocd/bootstrap/application.yaml")
    before = copy.deepcopy(root)
    app = child("app", [{"repoURL": root["spec"]["source"]["repoURL"], "path": "apps/app"}])
    children = [] if case == "unknown" else [app]
    if case == "duplicate":
        children.append(copy.deepcopy(app))
    if case == "ambiguous":
        app["spec"]["source"] = {"repoURL": "https://example.test"}
    with pytest.raises(ValueError):
        prepare(root, children, "HEAD" if case == "head" else "codex/preview", "app")
    assert root == before
