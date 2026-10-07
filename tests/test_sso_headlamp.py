from __future__ import annotations

import json
import subprocess
import sys

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


def test_inventory_alone_preserves_oidc_access_on_every_node() -> None:
    # A standard upstream run without extra-vars must retain OIDC login. The
    # addon-deletion tests only protect namespace and credential ownership.
    inventory = json.loads(
        subprocess.check_output(
            [
                sys.executable,
                "-m",
                "ansible.cli.inventory",
                "-i",
                str(ROOT / "inventory/soycluster/hosts.yml"),
                "--list",
            ],
            cwd=ROOT,
            text=True,
        )
    )
    hosts = inventory["_meta"]["hostvars"]
    assert set(hosts) == {"node-0", "node-1", "node-2"}
    for host, values in hosts.items():
        assert values.get("kube_oidc_auth") is True, host
        assert values.get("kube_oidc_url") == "https://auth.soyspray.vip/application/o/headlamp/", (
            host
        )
        assert values.get("kube_oidc_client_id") == "headlamp", host
        assert values.get("kube_oidc_username_claim") == "preferred_username", host
        assert values.get("kube_oidc_groups_claim") == "groups", host
        assert values.get("kube_oidc_username_prefix") == "oidc:", host
        assert values.get("kube_oidc_groups_prefix") == "oidc:", host


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
