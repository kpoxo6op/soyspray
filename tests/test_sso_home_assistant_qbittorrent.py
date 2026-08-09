from __future__ import annotations

from conftest import ROOT, load_yaml


def test_home_assistant_installs_the_pinned_oidc_release() -> None:
    deployment = load_yaml(
        "playbooks/argocd/applications/home-automation/home-assistant/deployment.yaml"
    )
    init_containers = {
        item["name"]: item for item in deployment["spec"]["template"]["spec"]["initContainers"]
    }
    installer = init_containers["install-oidc-auth"]
    script = installer["command"][-1]

    assert installer["image"] == "alpine:3.20"
    assert "v1.1.1" in script
    assert "hass-oidc-auth.zip" in script
    assert "9ce9e6153f80c781e360b93e097ff7d87d09235430fc48e7a67d97dda5fc3322" in script
    assert 'install_dir="/config/custom_components/auth_oidc"' in script


def test_home_assistant_uses_authentik_and_keeps_native_recovery() -> None:
    bootstrap = load_yaml(
        "playbooks/argocd/applications/home-automation/home-assistant/configmap-bootstrap.yaml"
    )["data"]["configuration.yaml"]

    assert "auth_oidc:" in bootstrap
    assert "client_id: home-assistant" in bootstrap
    assert (
        "discovery_url: https://auth.soyspray.vip/application/o/home-assistant/"
        ".well-known/openid-configuration" in bootstrap
    )
    assert "display_name: Authentik" in bootstrap
    assert "include_groups_scope: false" in bootstrap
    assert "automatic_user_linking: false" in bootstrap
    assert "admin: cluster-admins" in bootstrap
    assert "default_redirect: false" in bootstrap
    assert "auth_providers:" not in bootstrap


def test_authentik_deploys_home_assistant_from_the_tested_revision() -> None:
    defaults = load_yaml("roles/apps/homeassistant/defaults/main.yml")
    tasks = (ROOT / "roles/apps/homeassistant/tasks/main.yml").read_text()
    authentik_tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert defaults["homeassistant_target_revision"] == "HEAD"
    assert "home-assistant/homeassistant-application.yaml" in tasks
    assert "homeassistant_target_revision" in tasks
    assert "- name: Apply Home Assistant SSO" not in authentik_tasks


def test_qbittorrent_accepts_authentik_basic_auth_and_keeps_native_api() -> None:
    deployment = load_yaml("playbooks/argocd/applications/media/qbittorrent/deployment.yaml")
    image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
    ingress = load_yaml("playbooks/argocd/applications/media/qbittorrent/ingress.yaml")
    response_headers = set(
        ingress["metadata"]["annotations"][
            "nginx.ingress.kubernetes.io/auth-response-headers"
        ].split(",")
    )
    blueprint = (
        ROOT
        / "playbooks/argocd/applications/security/authentik/blueprints/legacy-forward-auth.yaml"
    ).read_text()

    assert image == "linuxserver/qbittorrent:libtorrentv1-5.2.3_v1.2.20-ls126"
    assert "Authorization" in response_headers
    assert "basic_auth_enabled: true" in blueprint
    assert "basic_auth_user_attribute: qbittorrent_username" in blueprint
    assert "basic_auth_password_attribute: qbittorrent_password" in blueprint
    assert "intercept_header_auth: false" in blueprint
    assert "skip_path_regex: ^/api/v2(/|$)" in blueprint


def test_qbittorrent_basic_auth_values_stay_in_the_runtime_secret() -> None:
    cluster_blueprint = (
        ROOT / "playbooks/argocd/applications/security/authentik/blueprints/cluster-sso.yaml"
    ).read_text()
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert "qbittorrent_username: !Env QBITTORRENT_WEB_USERNAME" in cluster_blueprint
    assert "qbittorrent_password: !Env QBITTORRENT_WEB_PASSWORD" in cluster_blueprint
    assert "QBITTORRENT_WEB_USERNAME" in tasks
    assert "QBITTORRENT_WEB_PASSWORD" in tasks
