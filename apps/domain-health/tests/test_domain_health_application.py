from pathlib import Path

import yaml

APP = Path(__file__).resolve().parents[1]


def test_native_ownership_keeps_workload_names_and_bootstrap_secret_boundary():
    application = yaml.safe_load((APP / "argocd/application.yaml").read_text())
    project = yaml.safe_load((APP / "argocd/project.yaml").read_text())
    assert application["metadata"]["name"] == "domain-health"
    assert application["metadata"].get("finalizers", []) == []
    assert (
        application["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
        == "Prune=false,Delete=false"
    )
    assert application["spec"]["project"] == project["metadata"]["name"] == "domain-health"
    assert application["spec"]["destination"] in project["spec"]["destinations"]
    assert project["spec"]["clusterResourceWhitelist"] == []
    assert {
        (item["group"], item["kind"]) for item in project["spec"]["namespaceResourceWhitelist"]
    } == {("", "ConfigMap"), ("", "Service"), ("apps", "Deployment")}
    source = APP.parents[1] / application["spec"]["source"]["path"]
    deployment = yaml.safe_load((source / "deployment.yaml").read_text())
    assert deployment["metadata"]["name"] == "domain-health"
    assert deployment["spec"]["selector"]["matchLabels"] == {
        "app.kubernetes.io/name": "domain-health"
    }
    env = deployment["spec"]["template"]["spec"]["containers"][0]["env"]
    assert {
        item["name"]: item["valueFrom"]["secretKeyRef"] for item in env if "valueFrom" in item
    } == {
        "CLOUDFLARE_API_TOKEN": {"name": "cloudflare-api-token", "key": "api-token"},
        "HEALTHCHECKS_PING_URL": {"name": "domain-health-config", "key": "healthchecks-ping-url"},
        "EXPECTED_NAMESERVERS": {"name": "domain-health-config", "key": "expected-nameservers"},
    }
