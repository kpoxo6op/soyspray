from __future__ import annotations

from conftest import ROOT, load_all, load_yaml

AUTHENTIK_DIR = ROOT / "playbooks/argocd/applications/security/authentik"


def test_authentik_uses_pinned_official_chart_and_external_database() -> None:
    app = load_yaml("playbooks/argocd/applications/security/authentik/authentik-application.yaml")
    chart = app["spec"]["sources"][0]
    values = load_yaml("playbooks/argocd/applications/security/authentik/values.yaml")

    assert chart["repoURL"] == "https://charts.goauthentik.io"
    assert chart["chart"] == "authentik"
    assert chart["targetRevision"] == "2026.5.6"
    assert app["spec"]["destination"]["namespace"] == "authentik"
    assert app["spec"]["syncPolicy"]["automated"] == {
        "prune": True,
        "selfHeal": True,
    }
    assert values["postgresql"]["enabled"] is False
    assert values["authentik"]["existingSecret"]["secretName"] == "authentik-runtime"
    assert values["blueprints"]["configMaps"] == ["authentik-blueprints"]


def test_authentik_database_is_dedicated_and_monitored() -> None:
    resources = load_all("playbooks/argocd/applications/security/authentik/database/cluster.yaml")
    cluster = next(item for item in resources if item["kind"] == "Cluster")

    assert cluster["metadata"]["name"] == "authentik-postgresql"
    assert cluster["metadata"]["namespace"] == "authentik"
    assert cluster["spec"]["instances"] >= 2
    assert cluster["spec"]["monitoring"]["enablePodMonitor"] is True
    assert cluster["spec"]["storage"]["storageClass"] == "longhorn"


def test_authentik_blueprint_reads_credentials_from_environment() -> None:
    blueprint = (AUTHENTIK_DIR / "blueprints/cluster-sso.yaml").read_text()

    assert "model: authentik_core.user" in blueprint
    assert "username: boris" in blueprint
    assert "cluster-admins" in blueprint
    assert "model: authentik_providers_oauth2.oauth2provider" in blueprint
    assert "model: authentik_core.application" in blueprint
    assert blueprint.count("model: authentik_blueprints.metaapplyblueprint") >= 4
    assert "!Env SSO_PASSWORD" in blueprint
    assert "!Env ARGOCD_OIDC_CLIENT_SECRET" in blueprint
    assert "!Env GRAFANA_OIDC_CLIENT_SECRET" in blueprint
    assert "client_secret:" not in blueprint.replace(
        "client_secret: !Env ARGOCD_OIDC_CLIENT_SECRET", ""
    ).replace("client_secret: !Env GRAFANA_OIDC_CLIENT_SECRET", "")


def test_authentik_role_preserves_generated_secrets() -> None:
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert "kubernetes.core.k8s_info" in tasks
    assert "authentik-runtime" in tasks
    assert "no_log: true" in tasks
    assert "lookup('password'" in tasks
    assert "state: present" in tasks
    assert "authentik-application.yaml" in tasks


def test_argocd_uses_authentik_oidc_and_keeps_local_admin() -> None:
    config = load_yaml("playbooks/argocd/config/argocd-cm.yaml")["data"]
    rbac = load_yaml("playbooks/argocd/config/argocd-rbac-cm.yaml")["data"]

    assert "auth.soyspray.vip" in config["oidc.config"]
    assert "$oidc.authentik.clientSecret" in config["oidc.config"]
    assert config.get("admin.enabled", "true") == "true"
    assert "cluster-admins" in rbac["policy.csv"]
    assert rbac["policy.default"] == "role:readonly"


def test_grafana_uses_authentik_and_disables_anonymous_access() -> None:
    values = load_yaml("playbooks/argocd/applications/observability/prometheus/values.yaml")
    grafana = values["grafana"]
    oauth = grafana["grafana.ini"]["auth.generic_oauth"]

    assert grafana["grafana.ini"]["auth.anonymous"]["enabled"] is False
    assert grafana["envFromSecret"] == "grafana-oidc"
    assert oauth["enabled"] is True
    assert oauth["auth_url"].startswith("https://auth.soyspray.vip/application/o/authorize/")
    assert oauth["client_secret"] == "$__env{GRAFANA_OIDC_CLIENT_SECRET}"
    assert "cluster-admins" in oauth["role_attribute_path"]


def test_prometheus_application_returns_to_the_reviewed_head_revision() -> None:
    app = load_yaml(
        "playbooks/argocd/applications/observability/prometheus/prometheus-application.yaml"
    )

    assert app["spec"]["source"]["targetRevision"] == "HEAD"
