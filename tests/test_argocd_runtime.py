import subprocess

import yaml
from conftest import ROOT


def test_runtime_render_keeps_private_inputs_and_pod_templates_out_of_ownership_changes():
    rendered = subprocess.check_output(
        ["kubectl", "kustomize", str(ROOT / "apps/argocd/manifests")], text=True
    )
    objects = list(yaml.safe_load_all(rendered))
    assert objects
    for obj in objects:
        assert obj["kind"] not in {"Secret", "ConfigMap"}
        assert (obj["kind"], obj["metadata"]["name"]) != ("Service", "argocd-server")
        options = set(obj["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(","))
        assert {"Prune=false", "Delete=false"} <= options
        if obj["kind"] in {"Deployment", "StatefulSet"}:
            annotations = obj["spec"]["template"]["metadata"].get("annotations", {})
            assert "argocd.argoproj.io/sync-options" not in annotations
