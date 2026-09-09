from __future__ import annotations

from conftest import ROOT, load_all, load_yaml

AUTHENTIK_DIR = ROOT / "apps/authentik/manifests"


def test_explicit_blueprint_apply_waits_for_published_files_and_skips_check_mode() -> None:
    tasks = load_yaml("apps/authentik/bootstrap/tasks/main.yml")
    apply = next(
        t for t in tasks if t.get("ansible.builtin.import_tasks") == "apply-blueprints.yml"
    )
    assert "not ansible_check_mode" in apply["when"]
    assert "'authentik-blueprints' in ansible_run_tags" in apply["when"]
    steps = load_yaml("apps/authentik/bootstrap/tasks/apply-blueprints.yml")
    wait = next(t for t in steps if "loop" in t)
    assert set(wait["loop"]) == {"cluster-sso.yaml", "native-apps.yaml", "legacy-forward-auth.yaml"}
    assert "hash('sha256')" in wait["until"]
    assert wait["changed_when"] is False
    command = steps[-1]["kubernetes.core.k8s_exec"]["command"].split()
    assert command[:2] == ["ak", "apply_blueprint"]
    assert set(command[2:]) == {f"mounted/cm-authentik-blueprints/{name}" for name in wait["loop"]}
    assert steps[-1]["no_log"] is True


def test_authentik_uses_pinned_official_chart_and_external_database() -> None:
    app = load_yaml("argocd/catalog/authentik.yaml")
    chart = app["spec"]["sources"][0]
    values = load_yaml("apps/authentik/manifests/values.yaml")

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
    resources = load_all("apps/authentik-postgresql/manifests/cluster.yaml")
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
    assert "id: media-users" in blueprint
    assert "- !KeyOf media-users" in blueprint
    assert "model: authentik_providers_oauth2.oauth2provider" in blueprint
    assert "model: authentik_core.application" in blueprint
    assert blueprint.count("model: authentik_blueprints.metaapplyblueprint") >= 4
    assert "!Env SSO_PASSWORD" in blueprint
    assert "!Env ARGOCD_OIDC_CLIENT_SECRET" in blueprint
    assert "!Env GRAFANA_OIDC_CLIENT_SECRET" in blueprint
    assert "client_secret:" not in blueprint.replace(
        "client_secret: !Env ARGOCD_OIDC_CLIENT_SECRET", ""
    ).replace("client_secret: !Env GRAFANA_OIDC_CLIENT_SECRET", "").replace(
        "client_secret: !Env HEADLAMP_OIDC_CLIENT_SECRET", ""
    )


def test_authentik_role_preserves_generated_secrets() -> None:
    tasks = (ROOT / "apps/authentik/bootstrap/tasks/main.yml").read_text()

    assert "kubernetes.core.k8s_info" in tasks
    assert "authentik-runtime" in tasks
    assert "no_log: true" in tasks
    assert "lookup('password'" in tasks
    assert "state: present" in tasks
    assert "kind: Application" not in tasks


def test_argocd_uses_authentik_oidc_and_keeps_local_admin() -> None:
    config = load_yaml("playbooks/argocd/config/argocd-cm.yaml")["data"]
    rbac = load_yaml("playbooks/argocd/config/argocd-rbac-cm.yaml")["data"]

    assert "auth.soyspray.vip" in config["oidc.config"]
    assert "$oidc.authentik.clientSecret" in config["oidc.config"]
    assert config["oidc.tls.insecure.skip.verify"] == "true"
    assert config.get("admin.enabled", "true") == "true"
    assert "cluster-admins" in rbac["policy.csv"]
    assert rbac["policy.default"] == "role:readonly"


def test_argocd_restarts_when_the_oidc_config_changes() -> None:
    tasks = (ROOT / "apps/authentik/bootstrap/tasks/main.yml").read_text()

    assert "soyspray.vip/oidc-config-hash" in tasks
    assert "argocd/config/argocd-cm.yaml') | hash('sha256')" in tasks


def test_grafana_uses_authentik_and_disables_anonymous_access() -> None:
    values = load_yaml("apps/prometheus/values.yaml")
    grafana = values["grafana"]
    oauth = grafana["grafana.ini"]["auth.generic_oauth"]

    assert grafana["grafana.ini"]["auth.anonymous"]["enabled"] is False
    assert grafana["envFromSecret"] == "grafana-oidc"
    assert oauth["enabled"] is True
    assert oauth["auth_url"].startswith("https://auth.soyspray.vip/application/o/authorize/")
    assert oauth["client_secret"] == "$__env{GRAFANA_OIDC_CLIENT_SECRET}"
    assert "cluster-admins" in oauth["role_attribute_path"]


def test_prometheus_application_returns_to_the_reviewed_head_revision() -> None:
    app = load_yaml("apps/prometheus/argocd/kube-prometheus-stack.yaml")

    assert app["spec"]["source"]["targetRevision"] == "main"
    assert app["spec"]["source"].get("kustomize", {}) == {}
    assert "retry" not in app["spec"]["syncPolicy"]["automated"]
    assert app["spec"]["syncPolicy"]["retry"]["limit"] == 5


def test_authentik_role_does_not_reuse_the_parent_loop_variable() -> None:
    tasks = (ROOT / "apps/authentik/bootstrap/tasks/main.yml").read_text()

    assert "loop_var: argocd_config_file" in tasks
