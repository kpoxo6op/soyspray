from __future__ import annotations

import subprocess

import pytest
from conftest import ROOT, load_yaml

APP_DIR = ROOT / "playbooks/argocd/applications/kong-bank-lab"
APP_FILES = sorted(APP_DIR.glob("*-application.yaml"))


def sources(app: dict) -> list[dict]:
    return app["spec"].get("sources", [app["spec"].get("source", {})])


def test_bank_lab_has_one_project_and_nine_apps() -> None:
    assert (APP_DIR / "banklab-kong-project.yaml").is_file()
    assert len(APP_FILES) == 9


def test_bank_lab_project_grants_only_rendered_resource_kinds() -> None:
    project = load_yaml("playbooks/argocd/applications/kong-bank-lab/banklab-kong-project.yaml")[
        "spec"
    ]
    namespace_kinds = {
        (item["group"], item["kind"]) for item in project["namespaceResourceWhitelist"]
    }
    cluster_kinds = {(item["group"], item["kind"]) for item in project["clusterResourceWhitelist"]}

    assert ("*", "*") not in namespace_kinds
    assert ("*", "*") not in cluster_kinds
    assert namespace_kinds == {
        ("", "ConfigMap"),
        ("", "Secret"),
        ("", "Service"),
        ("", "ServiceAccount"),
        ("apps", "Deployment"),
        ("configuration.konghq.com", "KongConsumer"),
        ("configuration.konghq.com", "KongPlugin"),
        ("gateway.networking.k8s.io", "Gateway"),
        ("gateway.networking.k8s.io", "HTTPRoute"),
        ("monitoring.coreos.com", "PodMonitor"),
        ("networking.k8s.io", "Ingress"),
        ("networking.k8s.io", "NetworkPolicy"),
        ("policy", "PodDisruptionBudget"),
        ("rbac.authorization.k8s.io", "Role"),
        ("rbac.authorization.k8s.io", "RoleBinding"),
    }
    assert cluster_kinds == {
        ("", "Namespace"),
        ("admissionregistration.k8s.io", "ValidatingAdmissionPolicy"),
        ("admissionregistration.k8s.io", "ValidatingAdmissionPolicyBinding"),
        ("admissionregistration.k8s.io", "ValidatingWebhookConfiguration"),
        ("apiextensions.k8s.io", "CustomResourceDefinition"),
        ("configuration.konghq.com", "KongClusterPlugin"),
        ("gateway.networking.k8s.io", "GatewayClass"),
        ("networking.k8s.io", "IngressClass"),
        ("rbac.authorization.k8s.io", "ClusterRole"),
        ("rbac.authorization.k8s.io", "ClusterRoleBinding"),
    }


@pytest.mark.parametrize("path", APP_FILES, ids=lambda path: path.stem)
def test_application_is_reconciling(path) -> None:
    app = load_yaml(str(path.relative_to(ROOT)))
    assert not (app["spec"].get("source") and app["spec"].get("sources"))
    assert app["spec"]["project"] == "banklab-kong"
    assert app["metadata"]["labels"]["app.kubernetes.io/part-of"] == "kong-bank-lab"
    assert app["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]
    assert app["spec"]["syncPolicy"]["automated"] == {"prune": True, "selfHeal": True}


@pytest.mark.parametrize("path", APP_FILES, ids=lambda path: path.stem)
def test_git_sources_point_to_existing_paths(path) -> None:
    app = load_yaml(str(path.relative_to(ROOT)))
    for source in sources(app):
        if source.get("repoURL", "").endswith("soyspray.git") and source.get("path"):
            assert (ROOT / source["path"]).exists()
        if source.get("repoURL", "").endswith("soyspray.git"):
            assert source["targetRevision"] == "HEAD"


def test_runtime_chart_has_one_crd_owner_and_consistent_tracking() -> None:
    runtime = load_yaml("playbooks/argocd/applications/kong-bank-lab/banklab-kong-application.yaml")
    chart_source = runtime["spec"]["sources"][0]
    assert runtime["metadata"]["name"] == chart_source["helm"]["releaseName"]
    assert chart_source["helm"]["skipCrds"] is True
    assert runtime["spec"]["syncPolicy"]["syncOptions"] == [
        "CreateNamespace=true",
        "RespectIgnoreDifferences=true",
    ]
    values = load_yaml("platform/kong/helm/values-kong-oss-baseline.yaml")
    assert values["controller"]["ingressController"]["installCRDs"] is False
    ignored = runtime["spec"]["ignoreDifferences"]
    assert {item["kind"] for item in ignored} == {
        "Secret",
        "ValidatingWebhookConfiguration",
    }

    crds = load_yaml(
        "playbooks/argocd/applications/kong-bank-lab/banklab-kong-crds-application.yaml"
    )
    assert crds["spec"]["source"]["chart"] == "kong"
    assert crds["spec"]["syncPolicy"]["syncOptions"] == [
        "CreateNamespace=true",
        "ServerSideApply=true",
    ]


def test_kong_webhook_only_checks_marked_plugin_secrets() -> None:
    values = load_yaml("platform/kong/helm/values-kong-oss-baseline.yaml")
    admission = values["controller"]["ingressController"]["admissionWebhook"]
    assert admission["filterSecrets"] is True


def test_make_help_stays_short() -> None:
    result = subprocess.run(["make", "help"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert len(result.stdout.splitlines()) < 30
    assert "goal" not in result.stdout.lower()


def test_makefile_has_no_imperative_cluster_apply() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "kubectl apply" not in makefile
    assert "--tags kong_bank_lab" in makefile
    assert "kong-on: go" in makefile
    assert "kong-off: go" in makefile
    assert "check: lint validate test docs" in makefile
    assert "ruff check" in makefile
    assert "ruff format --check" in makefile


def test_ci_uses_node24_actions() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v6" in workflow


def test_bank_lab_is_off_by_default() -> None:
    defaults = load_yaml("roles/apps/kong-bank-lab/defaults/main.yml")
    assert defaults["kong_bank_lab_enabled"] is False
    assert defaults["kong_bank_lab_target_revision"] == "HEAD"
    runtime_apps = defaults["kong_bank_lab_runtime_application_manifests"]
    assert "banklab-kong-crds-application.yaml" not in runtime_apps
    assert len(runtime_apps) == 8

    task_dir = ROOT / "roles/apps/kong-bank-lab/tasks"
    tasks = (task_dir / "main.yml").read_text()
    project_tasks = (task_dir / "project.yml").read_text()
    enabled_tasks = (task_dir / "enabled.yml").read_text()
    disabled_tasks = (task_dir / "disabled.yml").read_text()

    assert tasks.count("ansible.builtin.import_tasks:") == 3
    assert "project.yml" in tasks
    assert "enabled.yml" in tasks
    assert "disabled.yml" in tasks
    assert len(tasks.splitlines()) < 25
    assert "banklab-kong-crds-application.yaml" in project_tasks
    assert "banklab-kong-crds-application.yaml" not in enabled_tasks
    assert 'loop: "{{ kong_bank_lab_runtime_application_manifests }}"' in enabled_tasks
    assert "replace('--ref=HEAD'" in enabled_tasks
    assert "kong_bank_lab_target_revision" in enabled_tasks
    assert "Create missing Kong key credentials" in enabled_tasks
    assert "Create the missing Kong JWT credential" in enabled_tasks
    assert "runtime-generated-not-committed" in enabled_tasks
    # Parking must never reapply the checked-in Applications. Before merge their
    # HEAD paths do not exist yet, and rewriting a live branch revision to HEAD
    # can strand Argo's resource finalizer during deletion.
    assert "state: present" not in disabled_tasks
    assert "lookup('file'" not in disabled_tasks
    assert "kubernetes.core.k8s_info" in disabled_tasks
    assert "state: patched" in disabled_tasks
    assert "automated: null" in disabled_tasks
    assert "operation: null" in disabled_tasks
    assert "when:" in disabled_tasks
    assert "state: absent" in disabled_tasks
    assert "wait: true" in disabled_tasks
    assert "application_manifest | regex_replace" in disabled_tasks
    assert (
        "banklab-kong-crds-application.yaml"
        not in disabled_tasks.split("- name: Remove Kong bank-lab runtime applications", 1)[1]
    )


def test_multi_source_app_does_not_contain_null_source() -> None:
    app = load_yaml(
        "playbooks/argocd/applications/kong-bank-lab/"
        "banklab-kong-security-controls-application.yaml"
    )
    assert "source" not in app["spec"]
