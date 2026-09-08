import subprocess

import yaml
from conftest import ROOT, load_yaml


def rendered_children():
    result = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / "argocd")],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(yaml.safe_load_all(result.stdout))


def test_root_cannot_prune_or_cascade_and_only_manages_argo_objects():
    app = load_yaml("argocd/bootstrap/application.yaml")
    project = load_yaml("argocd/bootstrap/project.yaml")
    assert app["metadata"].get("finalizers", []) == []
    assert app["spec"]["syncPolicy"]["automated"]["prune"] is False
    assert app["spec"]["syncPolicy"]["automated"]["allowEmpty"] is False
    assert app["spec"]["project"] == project["metadata"]["name"]
    assert app["spec"]["source"]["path"] == "argocd"
    assert project["spec"]["clusterResourceWhitelist"] == []
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "argocd"}
    ]
    assert project["spec"]["namespaceResourceWhitelist"] == [
        {"group": "argoproj.io", "kind": "Application"},
        {"group": "argoproj.io", "kind": "ApplicationSet"},
        {"group": "argoproj.io", "kind": "AppProject"},
    ]


def test_children_have_explicit_projects_and_survive_parent_removal():
    children = rendered_children()
    projects = {
        child["metadata"]["name"]: child for child in children if child["kind"] == "AppProject"
    }
    identities = set()
    for child in children:
        assert child["kind"] in {"Application", "ApplicationSet", "AppProject"}
        metadata = child["metadata"]
        assert metadata["namespace"] == "argocd"
        identity = (child["kind"], metadata["name"])
        assert identity not in identities
        identities.add(identity)
        options = set(metadata["annotations"]["argocd.argoproj.io/sync-options"].split(","))
        assert {"Prune=false", "Delete=false"} <= options
        if child["kind"] == "Application":
            assert metadata.get("finalizers", []) == []
            assert metadata["labels"]["soyspray.vip/owner"]
            project = projects[child["spec"]["project"]]
            assert child["spec"]["destination"] in project["spec"]["destinations"]
            assert child["spec"]["destination"]["namespace"] != "argocd"

        if child["kind"] == "ApplicationSet":
            template = child["spec"]["template"]
            assert child["spec"]["syncPolicy"]["preserveResourcesOnDeletion"] is True
            assert template["metadata"].get("finalizers", []) == []
            assert template["metadata"]["labels"]["soyspray.vip/owner"]
            template_options = set(
                template["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
            )
            assert {"Prune=false", "Delete=false"} <= template_options
            project = projects[template["spec"]["project"]]
            assert template["spec"]["destination"] in project["spec"]["destinations"]


def test_all_soyspray_git_sources_follow_main():
    root = load_yaml("argocd/bootstrap/application.yaml")
    assert root["spec"]["source"]["targetRevision"] == "main"
    for child in rendered_children():
        if child["kind"] == "Application":
            specs = child["spec"].get("sources", [child["spec"].get("source", {})])
        elif child["kind"] == "ApplicationSet":
            specs = child["spec"]["template"]["spec"].get(
                "sources", [child["spec"]["template"]["spec"].get("source", {})]
            )
        else:
            continue
        for source in specs:
            if source.get("repoURL") == "https://github.com/kpoxo6op/soyspray.git":
                assert source["targetRevision"] == "main"
