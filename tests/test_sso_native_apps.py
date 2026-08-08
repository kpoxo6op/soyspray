from __future__ import annotations

import yaml
from conftest import ROOT

BLUEPRINT = ROOT / "playbooks/argocd/applications/security/authentik/blueprints/native-apps.yaml"
TASKS = ROOT / "roles/apps/authentik/tasks/native-apps.yml"


def _blueprint_entries() -> list[dict]:
    class BlueprintLoader(yaml.SafeLoader):
        pass

    def construct_tagged(loader: BlueprintLoader, _suffix: str, node: yaml.Node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        return loader.construct_mapping(node)

    BlueprintLoader.add_multi_constructor("!", construct_tagged)
    return yaml.load(BLUEPRINT.read_text(), Loader=BlueprintLoader)["entries"]


def test_native_app_blueprint_uses_exact_oidc_clients() -> None:
    entries = _blueprint_entries()
    providers = {
        item["id"]: item["attrs"]
        for item in entries
        if item["model"] == "authentik_providers_oauth2.oauth2provider"
    }

    immich = providers["immich-provider"]
    assert immich["client_type"] == "confidential"
    assert immich["client_id"] == "immich"
    assert immich["client_secret"] == "IMMICH_OIDC_CLIENT_SECRET"
    assert immich["grant_types"] == ["authorization_code", "refresh_token"]
    assert immich["redirect_uris"] == [
        {
            "matching_mode": "strict",
            "url": "https://immich.soyspray.vip/auth/login",
            "redirect_uri_type": "authorization",
        },
        {
            "matching_mode": "strict",
            "url": "https://immich.soyspray.vip/user-settings",
            "redirect_uri_type": "authorization",
        },
        {
            "matching_mode": "strict",
            "url": "app.immich:///oauth-callback",
            "redirect_uri_type": "authorization",
        },
    ]

    booklore = providers["booklore-provider"]
    assert booklore["client_type"] == "public"
    assert booklore["client_id"] == "booklore"
    assert "client_secret" not in booklore
    assert booklore["grant_types"] == ["authorization_code", "refresh_token"]
    assert booklore["redirect_uris"] == [
        {
            "matching_mode": "strict",
            "url": "https://booklore.soyspray.vip/oauth2-callback",
            "redirect_uri_type": "authorization",
        },
        {
            "matching_mode": "strict",
            "url": "booklore://oauth2-callback",
            "redirect_uri_type": "authorization",
        },
        {
            "matching_mode": "strict",
            "url": "https://booklore.soyspray.vip/login",
            "redirect_uri_type": "logout",
        },
    ]
    assert booklore["logout_method"] == "backchannel"
    assert booklore["logout_uri"] == (
        "https://booklore.soyspray.vip/api/v1/auth/oidc/backchannel-logout"
    )


def test_native_apps_are_limited_to_cluster_admins() -> None:
    entries = _blueprint_entries()
    applications = {
        item["id"]: item for item in entries if item["model"] == "authentik_core.application"
    }
    bindings = [item for item in entries if item["model"] == "authentik_policies.policybinding"]

    assert set(applications) == {"immich-application", "booklore-application"}
    assert {item["identifiers"]["target"] for item in bindings} == {
        "immich-application",
        "booklore-application",
    }
    assert all(
        item["attrs"]["group"] == ["authentik_core.group", ["name", "cluster-admins"]]
        for item in bindings
    )


def test_native_app_tasks_use_supported_admin_apis_idempotently() -> None:
    tasks = TASKS.read_text()

    assert "authentik_configure_native_apps | default(false)" in tasks
    assert "ansible.builtin.assert:" in tasks
    assert "SOYSPRAY_IMMICH_ADMIN_EMAIL" in tasks
    assert "SOYSPRAY_IMMICH_ADMIN_PASSWORD" in tasks
    assert "SOYSPRAY_BOOKLORE_ADMIN_USERNAME" in tasks
    assert "SOYSPRAY_BOOKLORE_ADMIN_PASSWORD" in tasks
    assert "no_log: true" in tasks

    immich_get = tasks.index("url: https://immich.soyspray.vip/api/system-config")
    immich_put = tasks.index("url: https://immich.soyspray.vip/api/system-config", immich_get + 1)
    booklore_get = tasks.index("url: https://booklore.soyspray.vip/api/v1/settings")
    booklore_put = tasks.index(
        "url: https://booklore.soyspray.vip/api/v1/settings", booklore_get + 1
    )
    assert immich_get < immich_put
    assert booklore_get < booklore_put
    assert tasks.count("method: GET") >= 2
    assert tasks.count("method: PUT") == 2
    assert tasks.count("changed_when: false") >= 4
    assert "when: authentik_immich_current_config.json != authentik_immich_sso_config" in tasks
    assert "when: not authentik_booklore_sso_is_current" in tasks
    assert "register: authentik_immich_admin_login" in tasks
    assert "register: authentik_booklore_admin_login" in tasks


def test_native_app_tasks_keep_local_accounts_and_link_existing_users() -> None:
    tasks = TASKS.read_text()

    assert "tokenEndpointAuthMethod: client_secret_post" in tasks
    assert "autoRegister: false" in tasks
    assert "passwordLogin" in tasks
    assert "enabled: true" in tasks
    assert "enableAutoProvisioning: false" in tasks
    assert "allowLocalAccountLinking: true" in tasks
    assert "OIDC_FORCE_ONLY_MODE" in tasks
    assert "value: false" in tasks
    assert "preferred_username" in tasks
    assert "openid profile email offline_access" in tasks
    assert "clientSecret: ''" in tasks
    assert "OIDC_GROUP_SYNC_MODE" in tasks
    assert "ON_LOGIN_ADDITIVE" in tasks


def test_immich_admin_password_reset_is_explicit_and_private() -> None:
    document = yaml.safe_load(TASKS.read_text())
    configure = document[0]
    reset = next(
        task
        for task in configure["block"]
        if task["name"] == "Reset the Immich administrator password"
    )
    query, execute = reset["block"]

    assert reset["when"] == [
        "authentik_reset_immich_admin_password | default(false) | bool",
        "not ansible_check_mode",
    ]
    assert reset["no_log"] is True

    info = query["kubernetes.core.k8s_info"]
    assert info["kind"] == "Pod"
    assert info["namespace"] == "immich"
    assert info["label_selectors"] == [
        "app.kubernetes.io/instance=immich",
        "app.kubernetes.io/name=server",
    ]
    assert info["field_selectors"] == ["status.phase=Running"]
    assert "resources | length == 1" in query["until"]
    assert "'Ready'" in query["until"]
    assert query["changed_when"] is False

    run = execute["kubernetes.core.k8s_exec"]
    assert run["container"] == "immich-server"
    assert "authentik_immich_server_pods.resources[0].metadata.name" in run["pod"]
    assert "/usr/src/app/server/bin/immich-admin reset-admin-password" in run["command"]
    assert '"$1"' in run["command"]
    assert "authentik_immich_admin_password | quote" in run["command"]
    assert execute["changed_when"] is True
    assert "rc != 0" in execute["failed_when"]
    assert "The admin password has been updated." in execute["failed_when"]

    names = [task["name"] for task in configure["block"]]
    assert names.index("Reset the Immich administrator password") < names.index(
        "Log in to Immich with the local administrator"
    )


def test_authentik_role_mounts_and_runs_native_app_configuration() -> None:
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert "IMMICH_OIDC_CLIENT_SECRET" in tasks
    assert "native-apps.yaml" in tasks
    assert "include_tasks: native-apps.yml" in tasks
    assert tasks.index("Apply Authentik") < tasks.index("include_tasks: native-apps.yml")
