import subprocess
from pathlib import Path

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/cert-manager-config"


def rendered():
    app = yaml.safe_load((APP / "argocd/application.yaml").read_text())
    source = ROOT / app["spec"]["source"]["path"]
    return app, list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(source)], text=True)
        )
    )


def test_project_can_manage_config_and_reflection_without_owning_the_foundation():
    application, resources = rendered()
    project = yaml.safe_load((APP / "argocd/project.yaml").read_text())
    cluster = {
        (entry["group"], entry["kind"]) for entry in project["spec"]["clusterResourceWhitelist"]
    }
    namespaced = {
        (entry["group"], entry["kind"]) for entry in project["spec"]["namespaceResourceWhitelist"]
    }
    assert cluster == {
        ("cert-manager.io", "ClusterIssuer"),
        ("rbac.authorization.k8s.io", "ClusterRole"),
        ("rbac.authorization.k8s.io", "ClusterRoleBinding"),
    }
    assert namespaced == {
        ("", "ServiceAccount"),
        ("apps", "Deployment"),
        ("cert-manager.io", "Certificate"),
    }
    assert project["spec"]["destinations"] == [application["spec"]["destination"]]
    assert application["spec"]["destination"]["namespace"] == "cert-manager"
    assert application["metadata"].get("finalizers", []) == []
    for resource in [application, project]:
        assert (
            resource["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
            == "Prune=false,Delete=false"
        )
    for resource in resources:
        group = resource["apiVersion"].split("/")[0] if "/" in resource["apiVersion"] else ""
        namespace = resource["metadata"].get("namespace")
        assert (group, resource["kind"]) in (namespaced if namespace else cluster)
        if namespace:
            assert namespace == "cert-manager"
        if resource["kind"] == "Deployment":
            assert resource["metadata"]["name"] == "secret-reflector"


def test_existing_issuer_and_certificate_identities_are_protected():
    _, resources = rendered()
    for resource in resources:
        if resource["kind"] not in {"Certificate", "ClusterIssuer"}:
            continue
        assert (
            resource["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
            == "Prune=false,Delete=false"
        )
        if resource["kind"] == "Certificate":
            assert resource["metadata"]["name"] in {"prod-cert", "test-cert"}
            assert resource["spec"]["secretName"] == resource["metadata"]["name"] + "-tls"
            expected = (
                "letsencrypt-prod"
                if resource["metadata"]["name"] == "prod-cert"
                else "letsencrypt-staging"
            )
            assert resource["spec"]["issuerRef"] == {"kind": "ClusterIssuer", "name": expected}
        else:
            assert resource["metadata"]["name"] in {"letsencrypt-prod", "letsencrypt-staging"}
            acme = resource["spec"]["acme"]
            assert acme["privateKeySecretRef"]["name"] == resource["metadata"]["name"]
            assert acme["solvers"][0]["dns01"]["cloudflare"]["apiTokenSecretRef"] == {
                "name": "cloudflare-api-token",
                "key": "api-token",
            }


def test_legacy_role_keeps_secret_bootstrap_without_competing_application_ownership():
    tasks = yaml.safe_load((ROOT / "roles/apps/cert-manager/tasks/main.yml").read_text())
    templar = Templar(loader=DataLoader(), variables={"playbook_dir": str(ROOT / "playbooks")})
    for task in tasks:
        if "kubernetes.core.k8s" in task:
            definition = templar.template(task["kubernetes.core.k8s"]["definition"])
            resource = yaml.safe_load(definition) if isinstance(definition, str) else definition
            assert resource["kind"] == "Secret"
            assert resource["metadata"]["name"] == "bitnami-oci-helm"
        elif "ansible.builtin.include_role" in task:
            assert task["ansible.builtin.include_role"]["name"] == "app-secret"
            assert task["vars"]["secret_name"] == "cloudflare-api-token"
        else:
            raise AssertionError("Unexpected legacy registration action")
