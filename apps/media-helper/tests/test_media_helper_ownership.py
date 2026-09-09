import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/media-helper"


def test_project_covers_only_existing_stateless_workload_kinds():
    application = yaml.safe_load((APP / "argocd/application.yaml").read_text())
    project = yaml.safe_load((APP / "argocd/project.yaml").read_text())
    source = ROOT / application["spec"]["source"]["path"]
    objects = list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(source)], text=True)
        )
    )
    allowed = {
        (entry["group"], entry["kind"]) for entry in project["spec"]["namespaceResourceWhitelist"]
    }
    assert allowed == {
        ("", "Service"),
        ("apps", "Deployment"),
        ("networking.k8s.io", "NetworkPolicy"),
    }
    assert project["spec"]["clusterResourceWhitelist"] == []
    assert application["spec"]["destination"] in project["spec"]["destinations"]
    assert application["spec"]["project"] == project["metadata"]["name"] == "media-helper"
    for obj in objects:
        assert obj["metadata"]["namespace"] == "media"
        group = obj["apiVersion"].split("/")[0] if "/" in obj["apiVersion"] else ""
        assert (group, obj["kind"]) in allowed
    deployment = next(obj for obj in objects if obj["kind"] == "Deployment")
    assert deployment["metadata"]["name"] == "media-helper"
    assert deployment["spec"]["selector"]["matchLabels"] == {"app": "media-helper"}
    assert not any(
        "persistentVolumeClaim" in v for v in deployment["spec"]["template"]["spec"]["volumes"]
    )
    assert application["metadata"].get("finalizers", []) == []
    assert (
        application["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
        == "Prune=false,Delete=false"
    )


def test_live_tv_bootstrap_does_not_manage_the_native_helper_or_applications():
    tasks = (ROOT / "apps/live-tv/bootstrap/tasks/enabled.yml").read_text()
    assert "media-helper" not in tasks
    assert "kind: Application" not in tasks
    assert "targetRevision" not in tasks
