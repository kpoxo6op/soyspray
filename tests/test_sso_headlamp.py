from __future__ import annotations

from conftest import ROOT, load_yaml


def test_headlamp_uses_an_external_oidc_secret_and_group_rbac() -> None:
    values = load_yaml("playbooks/argocd/applications/infrastructure/headlamp/values.yaml")

    assert values["config"]["oidc"]["secret"]["create"] is False
    assert values["config"]["oidc"]["externalSecret"] == {
        "enabled": True,
        "name": "headlamp-oidc",
    }

    manifests = "\n".join(values["extraManifests"])
    assert "kind: ClusterRoleBinding" in manifests
    assert "name: oidc:cluster-admins" in manifests
    assert "name: cluster-admin" in manifests


def test_authentik_restarts_when_runtime_oidc_clients_change() -> None:
    values = load_yaml("playbooks/argocd/applications/security/authentik/values.yaml")
    application = load_yaml(
        "playbooks/argocd/applications/security/authentik/authentik-application.yaml"
    )
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert "podAnnotations" not in values["server"]
    assert "podAnnotations" not in values["worker"]
    parameters = application["spec"]["sources"][0]["helm"]["parameters"]
    assert {item["name"] for item in parameters} == {
        r"server.podAnnotations.soyspray\.vip/runtime-secret-resource-version",
        r"worker.podAnnotations.soyspray\.vip/runtime-secret-resource-version",
    }
    assert {item["value"] for item in parameters} == {"AUTHENTIK_RUNTIME_SECRET_RESOURCE_VERSION"}
    assert "register: authentik_runtime_secret_apply" in tasks
    assert "authentik_runtime_secret_apply.result.metadata.resourceVersion" in tasks


def test_authentik_worker_probe_allows_blueprint_apply_time() -> None:
    values = load_yaml("playbooks/argocd/applications/security/authentik/values.yaml")

    for probe_name in ("livenessProbe", "readinessProbe", "startupProbe"):
        assert values["worker"][probe_name]["timeoutSeconds"] == 15


def test_authentik_has_a_headlamp_oidc_client() -> None:
    blueprint = (
        ROOT / "playbooks/argocd/applications/security/authentik/blueprints/cluster-sso.yaml"
    ).read_text()

    assert "id: headlamp-provider" in blueprint
    assert "client_id: headlamp" in blueprint
    assert "client_secret: !Env HEADLAMP_OIDC_CLIENT_SECRET" in blueprint
    assert "url: https://headlamp.soyspray.vip/oidc-callback" in blueprint
    assert "slug: headlamp" in blueprint


def test_kubernetes_oidc_flags_match_the_headlamp_provider() -> None:
    variables = load_yaml("playbooks/operations/security/kubernetes-authentik-oidc-vars.yml")

    assert variables == {
        "upgrade_cluster_setup": True,
        "kube_oidc_auth": True,
        "kube_oidc_url": "https://auth.soyspray.vip/application/o/headlamp/",
        "kube_oidc_client_id": "headlamp",
        "kube_oidc_username_claim": "preferred_username",
        "kube_oidc_username_prefix": "oidc:",
        "kube_oidc_groups_claim": "groups",
        "kube_oidc_groups_prefix": "oidc:",
    }


def test_authentik_role_creates_and_deploys_headlamp_oidc() -> None:
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert "HEADLAMP_OIDC_CLIENT_SECRET" in tasks
    assert "name: headlamp-oidc" in tasks
    assert "OIDC_ISSUER_URL" in tasks
    assert "headlamp-application.yaml" in tasks
    assert "authentik_target_revision" in tasks
