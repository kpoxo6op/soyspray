from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from conftest import ROOT, load_all, load_yaml

BLUEPRINT = ROOT / (
    "playbooks/argocd/applications/security/authentik/blueprints/legacy-forward-auth.yaml"
)

APPLICATIONS = {
    "longhorn": {
        "directory": "playbooks/argocd/applications/infrastructure/longhorn",
        "host": "longhorn.soyspray.vip",
        "namespace": "longhorn-system",
        "config_map": "auth-proxy-set-headers-longhorn",
        "service": "authentik-server-longhorn",
    },
    "prometheus": {
        "directory": "playbooks/argocd/applications/observability/prometheus",
        "host": "prometheus.soyspray.vip",
        "namespace": "monitoring",
        "config_map": "auth-proxy-set-headers-prometheus",
        "service": "authentik-server-prometheus",
    },
    "zigbee2mqtt": {
        "directory": "playbooks/argocd/applications/home-automation/zigbee2mqtt",
        "host": "zigbee2mqtt.soyspray.vip",
        "namespace": "home-automation",
        "config_map": "auth-proxy-set-headers-zigbee2mqtt",
        "service": "authentik-server-zigbee2mqtt",
    },
    "lazylibrarian": {
        "directory": "playbooks/argocd/applications/media/lazylibrarian",
        "host": "lazylibrarian.soyspray.vip",
        "namespace": "media",
        "config_map": "auth-proxy-set-headers-lazylibrarian",
        "service": "authentik-server-lazylibrarian",
    },
    "qbittorrent": {
        "directory": "playbooks/argocd/applications/media/qbittorrent",
        "host": "torrent.soyspray.vip",
        "namespace": "media",
        "config_map": "auth-proxy-set-headers-qbittorrent",
        "service": "authentik-server-qbittorrent",
    },
}

AUTH_ANNOTATIONS = {
    "nginx.ingress.kubernetes.io/auth-url",
    "nginx.ingress.kubernetes.io/auth-signin",
    "nginx.ingress.kubernetes.io/auth-response-headers",
    "nginx.ingress.kubernetes.io/auth-proxy-set-headers",
}


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


def _ingress_annotations(name: str) -> dict[str, str]:
    if name == "longhorn":
        return load_yaml(f"{APPLICATIONS[name]['directory']}/values.yaml")["ingress"]["annotations"]
    if name == "prometheus":
        return load_yaml(f"{APPLICATIONS[name]['directory']}/values.yaml")["prometheus"]["ingress"][
            "annotations"
        ]
    return load_yaml(f"{APPLICATIONS[name]['directory']}/ingress.yaml")["metadata"]["annotations"]


def test_blueprint_has_five_bound_single_application_proxy_providers() -> None:
    entries = _blueprint_entries()
    dependencies = {
        item["attrs"]["identifiers"]["name"]
        for item in entries
        if item["model"] == "authentik_blueprints.metaapplyblueprint"
    }
    providers = [
        item for item in entries if item["model"] == "authentik_providers_proxy.proxyprovider"
    ]
    applications = [item for item in entries if item["model"] == "authentik_core.application"]
    bindings = [item for item in entries if item["model"] == "authentik_policies.policybinding"]
    outposts = [item for item in entries if item["model"] == "authentik_outposts.outpost"]

    assert len(providers) == 5
    assert {item["attrs"]["external_host"] for item in providers} == {
        f"https://{settings['host']}" for settings in APPLICATIONS.values()
    }
    assert {item["attrs"]["mode"] for item in providers} == {"forward_single"}
    assert len(applications) == 5
    assert len(bindings) == 5
    assert all(
        item["attrs"]["group"] == ["authentik_core.group", ["name", "cluster-admins"]]
        for item in bindings
    )
    assert len(outposts) == 1
    assert outposts[0]["identifiers"]["managed"] == "goauthentik.io/outposts/embedded"
    assert len(outposts[0]["attrs"]["providers"]) == 5
    assert outposts[0]["attrs"]["config"] == {
        "authentik_host": "http://localhost:9000",
        "authentik_host_browser": "https://auth.soyspray.vip",
    }
    assert "Soyspray cluster SSO" in dependencies
    assert "System - Proxy Provider - Scopes" in dependencies


def test_blueprint_preserves_native_machine_api_paths() -> None:
    entries = _blueprint_entries()
    providers = {
        item["id"]: item["attrs"]
        for item in entries
        if item["model"] == "authentik_providers_proxy.proxyprovider"
    }

    assert providers["lazylibrarian-proxy-provider"]["skip_path_regex"] == (
        r"^/(api|opds|rss_feed)(/|$)|^/nzbfile\.nzb(/|$)"
    )
    assert providers["qbittorrent-proxy-provider"]["skip_path_regex"] == r"^/api/v2(/|$)"
    assert all(
        "skip_path_regex" not in providers[f"{name}-proxy-provider"]
        for name in ("longhorn", "prometheus", "zigbee2mqtt")
    )


def test_each_web_ingress_uses_authentik_forward_auth() -> None:
    response_headers = {
        "Set-Cookie",
        "X-authentik-username",
        "X-authentik-groups",
        "X-authentik-entitlements",
        "X-authentik-email",
        "X-authentik-name",
        "X-authentik-uid",
    }

    for name, settings in APPLICATIONS.items():
        annotations = _ingress_annotations(name)

        assert AUTH_ANNOTATIONS <= annotations.keys()
        assert annotations["nginx.ingress.kubernetes.io/auth-url"] == (
            "http://authentik-server.authentik.svc.cluster.local/outpost.goauthentik.io/auth/nginx"
        )
        assert annotations["nginx.ingress.kubernetes.io/auth-signin"] == (
            f"https://{settings['host']}/outpost.goauthentik.io/start?"
            "rd=$scheme://$http_host$escaped_request_uri"
        )
        assert (
            set(annotations["nginx.ingress.kubernetes.io/auth-response-headers"].split(","))
            == response_headers
        )
        assert annotations["nginx.ingress.kubernetes.io/auth-proxy-set-headers"] == (
            f"{settings['namespace']}/{settings['config_map']}"
        )


def test_each_application_owns_its_outpost_route_and_namespace_support() -> None:
    for settings in APPLICATIONS.values():
        directory = Path(settings["directory"])
        resources = load_all(f"{directory}/authentik-forward-auth.yaml")
        by_kind = {item["kind"]: item for item in resources}
        kustomization = load_yaml(f"{directory}/kustomization.yaml")

        assert "authentik-forward-auth.yaml" in kustomization["resources"]
        assert by_kind["ConfigMap"]["metadata"]["name"] == settings["config_map"]
        assert by_kind["ConfigMap"]["data"]["X-Forwarded-Host"] == "$http_host"
        assert by_kind["Service"]["metadata"]["name"] == settings["service"]
        assert by_kind["Service"]["spec"] == {
            "type": "ExternalName",
            "externalName": "authentik-server.authentik.svc.cluster.local",
            "ports": [
                {
                    "name": "http",
                    "port": 80,
                    "protocol": "TCP",
                    "targetPort": 80,
                }
            ],
        }

        ingress = by_kind["Ingress"]
        assert not (AUTH_ANNOTATIONS & ingress["metadata"].get("annotations", {}).keys())
        rule = ingress["spec"]["rules"][0]
        assert rule["host"] == settings["host"]
        path = rule["http"]["paths"][0]
        assert path["path"] == "/outpost.goauthentik.io"
        assert path["pathType"] == "Prefix"
        assert path["backend"]["service"]["name"] == settings["service"]
        assert path["backend"]["service"]["port"]["number"] == 80


def test_external_name_services_render_without_application_selectors() -> None:
    for name in ("zigbee2mqtt", "qbittorrent"):
        settings = APPLICATIONS[name]
        result = subprocess.run(
            ["kubectl", "kustomize", settings["directory"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        resources = [item for item in yaml.safe_load_all(result.stdout) if item]
        service = next(
            item
            for item in resources
            if item["kind"] == "Service" and item["metadata"]["name"] == settings["service"]
        )

        assert "selector" not in service["spec"]


def test_zigbee2mqtt_keeps_its_live_immutable_selector() -> None:
    deployment = load_yaml(
        "playbooks/argocd/applications/home-automation/zigbee2mqtt/deployment.yaml"
    )
    selector = deployment["spec"]["selector"]["matchLabels"]
    pod_labels = deployment["spec"]["template"]["metadata"]["labels"]

    assert selector == {"app": "zigbee2mqtt", "managed-by": "argocd"}
    assert selector.items() <= pod_labels.items()


def test_prometheus_and_qbittorrent_have_no_direct_web_load_balancer_bypass() -> None:
    prometheus = load_yaml("playbooks/argocd/applications/observability/prometheus/values.yaml")[
        "prometheus"
    ]["service"]
    qbittorrent = load_yaml("playbooks/argocd/applications/media/qbittorrent/service.yaml")["spec"]

    assert prometheus == {"type": "ClusterIP"}
    assert qbittorrent["type"] == "ClusterIP"
    assert "loadBalancerIP" not in qbittorrent


def test_authentik_role_mounts_and_deploys_legacy_proxy_configuration() -> None:
    tasks = (ROOT / "roles/apps/authentik/tasks/main.yml").read_text()

    assert "legacy-forward-auth.yaml" in tasks
    for manifest in (
        "longhorn-application.yaml",
        "zigbee2mqtt-application.yaml",
        "lazylibrarian-application.yaml",
        "qbittorrent-application.yaml",
    ):
        assert manifest in tasks
    assert tasks.count("authentik_target_revision") >= 6
    assert "loop_var: authentik_legacy_application" in tasks
