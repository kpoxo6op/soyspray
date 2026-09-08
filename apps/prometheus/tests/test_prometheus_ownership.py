from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ARGO = ROOT / "apps/prometheus/argocd"


def load(name):
    return yaml.safe_load((ARGO / name).read_text())


def entries(project, scope):
    return {(item["group"], item["kind"]) for item in project["spec"][scope]}


def test_existing_applications_use_separate_protected_projects():
    stack = load("kube-prometheus-stack.yaml")
    crds = load("prometheus-crds.yaml")

    assert stack["metadata"]["name"] == "kube-prometheus-stack"
    assert stack["metadata"].get("finalizers", []) == []
    assert stack["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "1"
    assert stack["spec"]["project"] == "prometheus-stack"
    assert stack["spec"]["source"] == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "main",
        "path": "apps/prometheus",
    }
    assert stack["spec"]["syncPolicy"]["automated"]["prune"] is False

    assert crds["metadata"]["name"] == "prometheus-crds"
    assert crds["metadata"].get("finalizers", []) == []
    assert crds["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "0"
    assert crds["spec"]["project"] == "prometheus-crds"
    assert crds["spec"]["source"] == {
        "repoURL": "https://prometheus-community.github.io/helm-charts",
        "chart": "prometheus-operator-crds",
        "targetRevision": "16.0.1",
    }
    assert crds["spec"]["syncPolicy"]["automated"]["prune"] is False

    for application in (stack, crds):
        assert application["metadata"]["labels"]["soyspray.vip/owner"] == "platform"
        assert (
            application["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
            == "Prune=false,Delete=false"
        )


def test_projects_keep_crd_permissions_separate_from_stack_permissions():
    stack = load("prometheus-stack-project.yaml")
    crds = load("prometheus-crds-project.yaml")

    assert stack["metadata"]["name"] == "prometheus-stack"
    assert stack["spec"]["sourceRepos"] == ["https://github.com/kpoxo6op/soyspray.git"]
    assert {item["namespace"] for item in stack["spec"]["destinations"]} == {
        "monitoring",
        "kube-system",
    }
    assert entries(stack, "clusterResourceWhitelist") == {
        ("", "Namespace"),
        ("admissionregistration.k8s.io", "MutatingWebhookConfiguration"),
        ("admissionregistration.k8s.io", "ValidatingWebhookConfiguration"),
        ("rbac.authorization.k8s.io", "ClusterRole"),
        ("rbac.authorization.k8s.io", "ClusterRoleBinding"),
    }
    assert entries(stack, "namespaceResourceWhitelist") == {
        ("", "ConfigMap"),
        ("", "Secret"),
        ("", "Service"),
        ("", "ServiceAccount"),
        ("apps", "DaemonSet"),
        ("apps", "Deployment"),
        ("batch", "Job"),
        ("monitoring.coreos.com", "Alertmanager"),
        ("monitoring.coreos.com", "PodMonitor"),
        ("monitoring.coreos.com", "Prometheus"),
        ("monitoring.coreos.com", "PrometheusRule"),
        ("monitoring.coreos.com", "ServiceMonitor"),
        ("networking.k8s.io", "Ingress"),
        ("rbac.authorization.k8s.io", "Role"),
        ("rbac.authorization.k8s.io", "RoleBinding"),
    }

    assert crds["metadata"]["name"] == "prometheus-crds"
    assert crds["spec"]["sourceRepos"] == ["https://prometheus-community.github.io/helm-charts"]
    assert entries(crds, "clusterResourceWhitelist") == {
        ("apiextensions.k8s.io", "CustomResourceDefinition")
    }
    assert crds["spec"]["namespaceResourceWhitelist"] == []

    for project in (stack, crds):
        assert (
            project["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
            == "Prune=false,Delete=false"
        )
