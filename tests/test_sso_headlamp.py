from __future__ import annotations

from conftest import ROOT, load_yaml


def test_headlamp_uses_an_external_oidc_secret_and_group_rbac() -> None:
    values = load_yaml("apps/headlamp/values.yaml")

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
    values = load_yaml("apps/authentik/manifests/values.yaml")
    application = load_yaml("argocd/catalog/authentik.yaml")
    tasks = (ROOT / "apps/authentik/bootstrap/tasks/main.yml").read_text()

    assert "podAnnotations" not in values["server"]
    assert "podAnnotations" not in values["worker"]
    assert "parameters" not in application["spec"]["sources"][0]["helm"]
    assert "register: authentik_runtime_secret_apply" in tasks
    assert "authentik_runtime_secret_apply.result.metadata.resourceVersion" not in tasks
    assert "soyspray.vip/runtime-secret-hash" in tasks
    consumer_tasks = [
        task
        for task in load_yaml("apps/authentik/bootstrap/tasks/main.yml")
        if task["name"]
        in {
            "Read Authentik deployments that consume the runtime secret",
            "Restart existing Authentik consumers when the runtime secret changes",
        }
    ]
    assert len(consumer_tasks) == 2
    assert "when" not in consumer_tasks[0]
    assert consumer_tasks[1]["when"] == ["item.resources | length == 1"]


def test_authentik_worker_probe_allows_blueprint_apply_time() -> None:
    values = load_yaml("apps/authentik/manifests/values.yaml")

    for probe_name in ("livenessProbe", "readinessProbe", "startupProbe"):
        assert values["worker"][probe_name]["timeoutSeconds"] == 15


def test_authentik_has_a_headlamp_oidc_client() -> None:
    blueprint = (ROOT / "apps/authentik/manifests/blueprints/cluster-sso.yaml").read_text()

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


def test_authentik_bootstraps_the_existing_headlamp_oidc_secret() -> None:
    tasks = load_yaml("apps/authentik/bootstrap/tasks/main.yml")
    secrets = [
        task
        for task in tasks
        if isinstance(definition := task.get("kubernetes.core.k8s", {}).get("definition"), dict)
        and definition.get("kind") == "Secret"
    ]
    task = next(
        task
        for task in secrets
        if task["kubernetes.core.k8s"]["definition"]["metadata"]["name"] == "headlamp-oidc"
    )
    secret = task["kubernetes.core.k8s"]["definition"]
    assert task["no_log"] is True
    assert secret["metadata"]["namespace"] == "headlamp"
    assert secret["stringData"] == {
        "OIDC_CLIENT_ID": "{{ authentik_runtime_values['HEADLAMP_OIDC_CLIENT_ID'] }}",
        "OIDC_CLIENT_SECRET": "{{ authentik_runtime_values['HEADLAMP_OIDC_CLIENT_SECRET'] }}",
        "OIDC_ISSUER_URL": "https://auth.soyspray.vip/application/o/headlamp/",
        "OIDC_SCOPES": "profile,email,offline_access",
    }
