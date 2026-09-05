from __future__ import annotations

import ast
import gzip
import importlib.util
import io
import json
import subprocess
from xml.etree import ElementTree as ET

import pytest
import yaml
from conftest import ROOT

HELPER = ROOT / "playbooks/argocd/applications/media/media-helper"
CATALOG = HELPER / "channels.json"
RECONCILE = ROOT / "playbooks/argocd/applications/media/dispatcharr/reconcile.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("media_helper", HELPER / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_reconcile():
    spec = importlib.util.spec_from_file_location("dispatcharr_reconcile", RECONCILE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_jellyfin_bootstrap_function(name: str):
    source = (ROOT / "playbooks/argocd/applications/media/jellyfin/bootstrap.py").read_text()
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "bootstrap.py", "exec"), namespace)
    return namespace[name]


def test_catalog_is_valid_and_has_unique_identity() -> None:
    helper = load_helper()
    catalog = json.loads(CATALOG.read_text())
    helper.validate_catalog(catalog)
    enabled = [channel for channel in catalog["channels"] if channel["enabled"]]
    assert {channel["slug"] for channel in enabled} >= {
        "otv-prim",
        "vostok-24",
        "25-region",
        "telemiks",
        "infinite-slop",
    }
    region = next(channel for channel in enabled if channel["slug"] == "25-region")
    assert region["sources"][0] == {
        "type": "streamlink_page",
        "url": "https://ok.ru/videoembed/7930222354061",
    }


def test_catalog_contains_only_jellyfin_channels() -> None:
    catalog = json.loads(CATALOG.read_text())

    assert "wall" not in catalog
    assert {channel["delivery"] for channel in catalog["channels"]} == {"dispatcharr"}
    assert not any(
        source["type"] == "youtube_url"
        for channel in catalog["channels"]
        for source in channel["sources"]
    )


def test_tv_hostname_keeps_jellyfin_as_its_root_application() -> None:
    jellyfin = ROOT / "playbooks/argocd/applications/media/jellyfin"
    ingress = yaml.safe_load((jellyfin / "ingress.yaml").read_text())

    assert ingress["spec"]["tls"][0]["hosts"] == ["tv.soyspray.vip"]
    assert [rule["host"] for rule in ingress["spec"]["rules"]] == ["tv.soyspray.vip"]
    paths = ingress["spec"]["rules"][0]["http"]["paths"]
    assert paths == [
        {
            "path": "/",
            "pathType": "Prefix",
            "backend": {"service": {"name": "jellyfin", "port": {"number": 8096}}},
        }
    ]

    assert not (HELPER / "ingress.yaml").exists()
    assert not (HELPER / "stream-ingress.yaml").exists()


def test_media_helper_has_no_browser_interface() -> None:
    helper = load_helper()
    kustomization = yaml.safe_load((HELPER / "kustomization.yaml").read_text())

    assert not (HELPER / "static").exists()
    assert not any("static/" in item for item in kustomization["configMapGenerator"][0]["files"])

    class Request:
        path = "/"
        catalog = helper.load_catalog(CATALOG)
        headers = {}

        def send(self, status, body, content_type):
            self.response = status, body, content_type

    request = Request()
    helper.Handler.do_GET(request)
    assert request.response == (404, b"not found\n", "text/plain")

    request.path = "/api/v1/channels"
    helper.Handler.do_GET(request)
    status, body, content_type = request.response
    assert status == 200
    assert content_type == "application/json"
    assert json.loads(body) == request.catalog


@pytest.mark.parametrize("field", ("slug", "number"))
def test_catalog_rejects_duplicate_channel_identity(field: str) -> None:
    helper = load_helper()
    catalog = json.loads(CATALOG.read_text())
    catalog["channels"][1][field] = catalog["channels"][0][field]
    with pytest.raises(ValueError, match=field):
        helper.validate_catalog(catalog)


def test_catalog_rejects_duplicate_guide_ids_and_signed_urls() -> None:
    helper = load_helper()
    catalog = json.loads(CATALOG.read_text())
    catalog["channels"][1]["guide"]["id"] = catalog["channels"][0]["guide"]["id"]
    with pytest.raises(ValueError, match="guide id"):
        helper.validate_catalog(catalog)

    catalog = json.loads(CATALOG.read_text())
    catalog["channels"][0]["sources"][0]["url"] += "?token=temporary"
    with pytest.raises(ValueError, match="signed"):
        helper.validate_catalog(catalog)


@pytest.mark.parametrize(
    "field,value,error",
    (
        ("delivery", "external", "unsupported delivery"),
        ("source", "youtube_url", "unsupported source"),
    ),
)
def test_catalog_rejects_channels_outside_jellyfin(field: str, value: str, error: str) -> None:
    helper = load_helper()
    catalog = json.loads(CATALOG.read_text())
    if field == "source":
        catalog["channels"][0]["sources"][0]["type"] = value
    else:
        catalog["channels"][0][field] = value

    with pytest.raises(ValueError, match=error):
        helper.validate_catalog(catalog)


def test_playlist_matches_xmltv_channel_identity() -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    playlist = helper.build_playlist(catalog, "http://media-helper.media.svc.cluster.local:8080")
    guide = helper.build_xmltv(catalog, {})
    assert "/play/" not in playlist
    for channel in catalog["channels"]:
        if channel["enabled"] and channel["delivery"] == "dispatcharr":
            assert f'tvg-id="{channel["guide"]["id"]}"' in playlist
            assert f'id="{channel["guide"]["id"]}"' in guide


def test_xmltv_exposes_a_native_jellyfin_tile_for_every_enabled_channel() -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    guide = ET.fromstring(helper.build_xmltv(catalog, {}).partition("\n")[2])
    xml_channels = {item.attrib["id"]: item for item in guide.findall("channel")}

    for channel in helper.dispatcharr_channels(catalog):
        assert channel["logo"], channel["slug"]
        icon = xml_channels[channel["guide"]["id"]].find("icon")
        assert icon is not None, channel["slug"]
        assert icon.attrib == {"src": channel["logo"]}


def test_playlist_keeps_all_ordered_sources_on_one_channel_identity() -> None:
    helper = load_helper()
    channel = {
        "slug": "test",
        "number": 7,
        "name": "Test channel",
        "enabled": True,
        "groups": ["Live TV"],
        "logo": "",
        "delivery": "dispatcharr",
        "sources": [
            {"type": "direct_hls", "url": "https://primary.example/live.m3u8"},
            {"type": "streamlink_page", "url": "https://fallback.example/live"},
        ],
        "guide": {"source": "none", "id": "test", "timezone": "UTC"},
    }
    playlist = helper.build_playlist({"channels": [channel]}, "https://tv.example")
    assert playlist.count('tvg-id="test"') == 2
    assert playlist.index("https://primary.example/live.m3u8") < playlist.index(
        "https://fallback.example/live"
    )


def test_guide_failure_keeps_channel_identity() -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    guide = helper.build_xmltv(catalog, {})
    assert guide.startswith("<?xml")
    assert "<programme" not in guide
    assert 'id="infinite-slop"' in guide


def test_catalog_uses_epg_lite_ids_for_broadcast_channels() -> None:
    catalog = json.loads(CATALOG.read_text())
    expected = {
        "otv-prim": "otv-primorie",
        "vostok-24": "vostok-24",
        "25-region": "25-region-vladik",
        "telemiks": "telemiks",
    }
    by_slug = {channel["slug"]: channel for channel in catalog["channels"]}
    for slug, guide_id in expected.items():
        assert by_slug[slug]["guide"] == {
            "source": "iptvx_epg_lite",
            "id": guide_id,
            "timezone": "Asia/Vladivostok",
        }


def test_epg_lite_parser_keeps_only_selected_programmes() -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <tv>
      <programme start="20260901100000 +0300" stop="20260901110000 +0300" channel="otv-primorie"><title lang="ru">News</title></programme>
      <programme start="20260901100000 +0300" stop="20260901110000 +0300" channel="not-selected"><title>Ignore</title></programme>
    </tv>"""
    programmes = helper.parse_epg_lite(io.BytesIO(gzip.compress(xml)), catalog)
    assert programmes["otv-prim"] == [
        {
            "times": {"start": "20260901100000 +0300", "stop": "20260901110000 +0300"},
            "title": "News",
        }
    ]
    assert all("Ignore" not in str(items) for items in programmes.values())


def test_guide_cache_keeps_last_non_empty_result_after_refresh_failure(monkeypatch) -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    required = [
        channel
        for channel in helper.dispatcharr_channels(catalog)
        if channel["guide"]["source"] == "iptvx_epg_lite"
    ]
    good = {
        channel["slug"]: [
            {
                "times": {
                    "start": "20260901100000 +0300",
                    "stop": "20260901110000 +0300",
                },
                "title": channel["name"],
            }
        ]
        for channel in required
    }
    calls = 0

    def fetch(_catalog):
        nonlocal calls
        calls += 1
        if calls == 1:
            return good
        raise OSError("upstream offline")

    monkeypatch.setattr(helper, "fetch_epg_lite", fetch)
    first_xml, first_programmes = helper.guide_snapshot(catalog, now=0)
    second_xml, second_programmes = helper.guide_snapshot(catalog, now=21601)
    third_xml, third_programmes = helper.guide_snapshot(catalog, now=21602)
    assert first_xml == second_xml
    assert first_xml == third_xml
    assert first_programmes == second_programmes == third_programmes == good
    assert calls == 2


def test_background_guide_refresh_is_single_flight_and_resets(monkeypatch) -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    targets = []
    calls = []

    class DeferredThread:
        def __init__(self, *, target, **_kwargs):
            targets.append(target)

        def start(self):
            pass

    monkeypatch.setattr(helper.threading, "Thread", DeferredThread)
    monkeypatch.setattr(helper, "guide_snapshot", lambda value: calls.append(value))

    helper.start_guide_refresh(catalog)
    helper.start_guide_refresh(catalog)
    assert len(targets) == 1
    assert helper.GUIDE_REFRESHING is True
    targets[0]()
    assert calls == [catalog]
    assert helper.GUIDE_REFRESHING is False

    def unavailable(value):
        calls.append(value)
        raise helper.GuideUnavailable

    monkeypatch.setattr(helper, "guide_snapshot", unavailable)
    helper.start_guide_refresh(catalog)
    targets[1]()
    assert calls == [catalog, catalog]
    assert helper.GUIDE_REFRESHING is False


def test_guide_cache_rejects_empty_or_missing_channels(monkeypatch) -> None:
    helper = load_helper()
    catalog = helper.load_catalog(CATALOG)
    monkeypatch.setattr(helper, "fetch_epg_lite", lambda _catalog: {"otv-prim": []})
    with pytest.raises(helper.GuideUnavailable):
        helper.guide_snapshot(catalog, now=0)


def test_voice_control_is_out_of_scope() -> None:
    catalog = json.loads(CATALOG.read_text())
    helper_source = (HELPER / "app.py").read_text()
    helper_deployment = yaml.safe_load((HELPER / "deployment.yaml").read_text())
    helper_env = helper_deployment["spec"]["template"]["spec"]["containers"][0].get("env", [])
    home_assistant = (
        ROOT
        / "playbooks/argocd/applications/home-automation/home-assistant/configmap-bootstrap.yaml"
    ).read_text()
    live_tv_tasks = (ROOT / "roles/apps/live_tv/tasks/enabled.yml").read_text()

    assert all("aliases" not in channel for channel in catalog["channels"])
    assert "play_on_jellyfin" not in helper_source
    assert "/jellyfin" not in helper_source
    assert not any(item["name"].startswith("JELLYFIN_") for item in helper_env)
    assert "play_live_tv_channel" not in home_assistant
    assert "Reconcile the Home Assistant Argo revision" not in live_tv_tasks


@pytest.mark.parametrize("name", ("media-helper", "dispatcharr", "jellyfin"))
def test_media_packages_render(name: str) -> None:
    path = f"playbooks/argocd/applications/media/{name}"
    result = subprocess.run(
        ["kubectl", "kustomize", path], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "@sha256:" in result.stdout


def test_media_helper_uses_server_side_apply_for_its_large_code_configmap() -> None:
    kustomization = yaml.safe_load((HELPER / "kustomization.yaml").read_text())
    assert kustomization["generatorOptions"]["annotations"] == {
        "argocd.argoproj.io/sync-options": "ServerSideApply=true"
    }


def test_stock_jellyfin_web_has_no_snapshot_workload() -> None:
    jellyfin = ROOT / "playbooks/argocd/applications/media/jellyfin"
    helper_kustomization = (HELPER / "kustomization.yaml").read_text()

    assert not (jellyfin / "web").exists()
    assert not (ROOT / ".github/workflows/jellyfin-image.yml").exists()
    assert not (HELPER / "snapshots.py").exists()
    assert "snapshot" not in helper_kustomization

    for name in ("dispatcharr", "jellyfin"):
        policy = (
            ROOT / f"playbooks/argocd/applications/media/{name}/network-policy.yaml"
        ).read_text()
        assert "channel-snapshots" not in policy


def test_jellyfin_storage_and_hardware_contract() -> None:
    deployment = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/jellyfin/deployment.yaml").read_text()
    )
    pod = deployment["spec"]["template"]["spec"]
    assert pod["nodeSelector"]["kubernetes.io/hostname"] == "node-0"
    assert pod["securityContext"]["supplementalGroups"] == [109]
    dri_volume = next(volume for volume in pod["volumes"] if volume["name"] == "dri")
    assert dri_volume["hostPath"] == {
        "path": "/dev/dri/renderD128",
        "type": "CharDevice",
    }
    assert any(
        volume.get("hostPath", {}).get("path") == "/srv/media/jellyfin-data"
        for volume in pod["volumes"]
    )
    jellyfin = pod["containers"][0]
    assert jellyfin["securityContext"]["privileged"] is True
    assert {"name": "JELLYFIN_DATA_DIR", "value": "/config/data"} in jellyfin["env"]
    dri = next(item for item in jellyfin["volumeMounts"] if item["name"] == "dri")
    assert dri["mountPath"] == "/dev/dri/renderD128"
    media = next(item for item in jellyfin["volumeMounts"] if item["name"] == "media")
    assert media["readOnly"] is True


def test_jellyfin_bootstrap_enables_qsv_without_losing_unknown_settings() -> None:
    current = {
        "HardwareAccelerationType": "none",
        "EnableHardwareEncoding": False,
        "VaapiDevice": "",
        "QsvDevice": "",
        "HardwareDecodingCodecs": ["h264", "vc1"],
        "UnknownFutureOption": {"keep": True},
    }

    desired = load_jellyfin_bootstrap_function("qsv_configuration")(current)

    assert desired == {
        **current,
        "HardwareAccelerationType": "qsv",
        "EnableHardwareEncoding": True,
        "QsvDevice": "/dev/dri/renderD128",
    }
    assert current["HardwareAccelerationType"] == "none"


def test_jellyfin_bootstrap_is_add_only_and_configures_live_tv() -> None:
    script = (ROOT / "playbooks/argocd/applications/media/jellyfin/bootstrap.py").read_text()
    assert 'call("GET", "/System/Configuration/livetv"' in script
    assert 'call("GET", "/LiveTv/TunerHosts"' not in script
    assert 'call("GET", "/LiveTv/ListingProviders"' not in script
    assert "/LiveTv/TunerHosts" in script
    assert "http://dispatcharr.media.svc.cluster.local:9191/hdhr" in script
    assert "/LiveTv/ListingProviders" in script
    assert "/DisplayPreferences/" not in script
    assert "VirtualFolders" in script
    assert "DELETE" not in script
    startup_get = script.index('call("GET", "/Startup/User")')
    startup_post = script.index('"/Startup/User",', startup_get)
    assert startup_get < startup_post
    job = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/jellyfin/bootstrap-job.yaml").read_text()
    )
    assert job["spec"]["activeDeadlineSeconds"] == 1200
    assert job["spec"]["backoffLimit"] == 0
    assert job["spec"]["template"]["spec"]["restartPolicy"] == "Never"
    policy = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/jellyfin/network-policy.yaml").read_text()
    )
    ingress = [peer for rule in policy["spec"]["ingress"] for peer in rule["from"]]
    assert {"podSelector": {"matchLabels": {"job-name": "jellyfin-bootstrap"}}} in ingress


@pytest.mark.parametrize(
    "name,claim", (("dispatcharr", "dispatcharr-data"), ("jellyfin", "jellyfin-config-v2"))
)
def test_configuration_claims_are_protected(name: str, claim: str) -> None:
    result = subprocess.run(
        ["kubectl", "kustomize", f"playbooks/argocd/applications/media/{name}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(result.stdout) if item]
    pvc = next(
        item
        for item in resources
        if item["kind"] == "PersistentVolumeClaim" and item["metadata"]["name"] == claim
    )
    assert pvc["metadata"]["annotations"] == {
        "argocd.argoproj.io/sync-options": "Delete=false,Prune=false"
    }
    if name == "jellyfin":
        assert pvc["spec"]["resources"]["requests"]["storage"] == "1Gi"


def test_required_feature_readmes_exist() -> None:
    paths = (
        "playbooks/argocd/applications/media/README.md",
        "playbooks/argocd/applications/media/jellyfin/README.md",
        "playbooks/argocd/applications/media/dispatcharr/README.md",
        "playbooks/argocd/applications/media/media-helper/README.md",
        "soydocs/android-tv/README.md",
    )
    for path in paths:
        assert (ROOT / path).is_file(), path


def test_live_tv_role_propagates_its_deployment_tag() -> None:
    tasks = yaml.safe_load((ROOT / "roles/apps/live_tv/tasks/main.yml").read_text())
    include = tasks[0]["ansible.builtin.include_tasks"]
    assert include["apply"]["tags"] == ["live-tv"]
    assert include["file"] == "{{ 'enabled.yml' if (live_tv_enabled | bool) else 'disabled.yml' }}"


def test_live_tv_prepares_secrets_before_it_changes_argo_revisions() -> None:
    tasks = yaml.safe_load((ROOT / "roles/apps/live_tv/tasks/enabled.yml").read_text())
    names = [task["name"] for task in tasks]
    assert names.index("Require the Jellyfin OIDC client secret") < names.index(
        "Apply the live TV Argo applications"
    )
    assert names.index("Create the stable Jellyfin secret") < names.index(
        "Apply the live TV Argo applications"
    )


def test_make_go_checks_authentik_and_live_tv_syntax() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "--tags authentik,live-tv" in makefile


def test_live_tv_start_reconciles_authentik_from_the_same_revision() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "LIVE_TV_TAGS := authentik,live-tv" in makefile
    assert "authentik_target_revision=$(LIVE_TV_REVISION)" in makefile
    assert "--tags $(LIVE_TV_TAGS)" in makefile


@pytest.mark.parametrize("name", ("media-helper", "dispatcharr", "jellyfin"))
def test_live_tv_applications_use_controlled_cascade(name: str) -> None:
    application = yaml.safe_load(
        (ROOT / f"playbooks/argocd/applications/media/{name}/{name}-application.yaml").read_text()
    )
    assert application["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]

    disabled = yaml.safe_load((ROOT / "roles/apps/live_tv/tasks/disabled.yml").read_text())
    quiesce = next(task for task in disabled if task["name"] == "Quiesce live TV Argo applications")
    assert quiesce["kubernetes.core.k8s"]["definition"]["metadata"]["finalizers"] == [
        "resources-finalizer.argocd.argoproj.io"
    ]
    removal = next(task for task in disabled if task["name"] == "Remove live TV Argo applications")
    assert removal["kubernetes.core.k8s"]["delete_options"] == {"propagationPolicy": "Foreground"}


def test_jellyfin_ingress_stays_private_without_forward_auth() -> None:
    ingress = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/jellyfin/ingress.yaml").read_text()
    )
    annotations = ingress["metadata"]["annotations"]
    assert annotations["nginx.ingress.kubernetes.io/whitelist-source-range"] == (
        "192.168.20.0/24,100.64.0.0/10,10.233.0.0/16"
    )
    assert not any("auth-" in key for key in annotations)


def test_dispatcharr_uses_forward_auth_and_jellyfin_keeps_client_api_open() -> None:
    auth_url = (
        "http://authentik-server.authentik.svc.cluster.local/outpost.goauthentik.io/auth/nginx"
    )
    response_headers = (
        "Set-Cookie,Authorization,X-authentik-username,X-authentik-groups,"
        "X-authentik-entitlements,X-authentik-email,X-authentik-name,X-authentik-uid"
    )
    dispatcharr = ROOT / "playbooks/argocd/applications/media/dispatcharr"
    ingress = yaml.safe_load((dispatcharr / "ingress.yaml").read_text())
    annotations = ingress["metadata"]["annotations"]
    assert annotations["nginx.ingress.kubernetes.io/auth-url"] == auth_url
    assert annotations["nginx.ingress.kubernetes.io/auth-signin"] == (
        "https://dispatcharr.soyspray.vip/outpost.goauthentik.io/start?"
        "rd=$scheme://$http_host$escaped_request_uri"
    )
    assert annotations["nginx.ingress.kubernetes.io/auth-proxy-set-headers"] == (
        "media/auth-proxy-set-headers-dispatcharr"
    )
    assert annotations["nginx.ingress.kubernetes.io/auth-response-headers"] == response_headers
    forward_auth = list(
        yaml.safe_load_all((dispatcharr / "authentik-forward-auth.yaml").read_text())
    )
    headers = next(item for item in forward_auth if item["kind"] == "ConfigMap")
    assert headers["data"] == {"X-Forwarded-Host": "$http_host"}
    assert headers["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-1"
    jellyfin = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/jellyfin/ingress.yaml").read_text()
    )
    assert not any("auth" in key for key in jellyfin["metadata"].get("annotations", {}))
    blueprint = (
        ROOT
        / "playbooks/argocd/applications/security/authentik/blueprints/legacy-forward-auth.yaml"
    ).read_text()
    assert "Dispatcharr forward auth" in blueprint


def test_dispatcharr_owns_its_authentik_outpost_route() -> None:
    dispatcharr = ROOT / "playbooks/argocd/applications/media/dispatcharr"
    forward_auth = list(
        yaml.safe_load_all((dispatcharr / "authentik-forward-auth.yaml").read_text())
    )
    service = next(item for item in forward_auth if item["kind"] == "Service")
    assert service["spec"] == {
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
    outpost_ingresses = {
        item["spec"]["rules"][0]["host"]: item for item in forward_auth if item["kind"] == "Ingress"
    }
    assert set(outpost_ingresses) == {"dispatcharr.soyspray.vip"}
    for ingress in outpost_ingresses.values():
        assert not ingress["metadata"].get("annotations")
        path = ingress["spec"]["rules"][0]["http"]["paths"][0]
        assert path == {
            "path": "/outpost.goauthentik.io",
            "pathType": "Prefix",
            "backend": {
                "service": {"name": "authentik-server-dispatcharr", "port": {"number": 80}}
            },
        }


def test_jellyfin_uses_pinned_oidc_plugin_and_declarative_authentik_config() -> None:
    root = ROOT / "playbooks/argocd/applications/media/jellyfin"
    deployment = yaml.safe_load((root / "deployment.yaml").read_text())
    pod = deployment["spec"]["template"]["spec"]
    installer = next(item for item in pod["initContainers"] if item["name"] == "install-sso")
    command = " ".join(installer["command"])
    assert "4.3.0.55" in command
    assert 'jellyfin_version = "10.11.11"' in command
    assert 'install_id = f"{version}-jellyfin-{jellyfin_version}"' in command
    assert "e066b312b96cc8133cca9711d9f5778e0bc64004e6cb9a6a6ed230f74b9808d8" in command
    assert installer["image"].startswith("python:3.13-alpine@sha256:")
    assert 'plugins = Path("/config/data/plugins")' in command
    assert {"name": "data", "mountPath": "/config/data"} in installer["volumeMounts"]
    jellyfin = pod["containers"][0]
    assert jellyfin["image"] == (
        "jellyfin/jellyfin:10.11.11@"
        "sha256:aefb67e6a7ff1debdd154a78a7bbb780fd0c873d8639210a7f6a2016ad2b35db"
    )
    env = {item["name"]: item for item in jellyfin["env"]}
    assert env["JELLYFIN_SSO_CONFIG_FILE"]["value"] == "/run/sso/providers.json"
    config = json.loads((root / "sso-config.json").read_text())
    provider = config["Configuration"]["OidConfigs"]["authentik"]
    assert provider["OidEndpoint"] == (
        "https://auth.soyspray.vip/application/o/jellyfin/.well-known/openid-configuration"
    )
    assert provider["OidSecretFile"] == "/run/secrets/jellyfin_oidc_client_secret"
    assert provider["Roles"] == ["media-users", "cluster-admins"]
    assert provider["AdminRoles"] == ["cluster-admins"]
    assert provider["EnableLiveTv"] is True
    assert provider["EnableLiveTvManagement"] is False
    assert provider["AllowPrivateNetworkAddresses"] is True
    assert "OidSecret" not in provider
    bootstrap = (root / "bootstrap.py").read_text()
    assert "505ce9d1-d916-42fa-86ca-673ef241d7df" in bootstrap
    assert "ManageLoginPageButtons" in bootstrap
    policy = yaml.safe_load((root / "network-policy.yaml").read_text())
    assert any(
        peer.get("namespaceSelector", {}).get("matchLabels", {}).get("kubernetes.io/metadata.name")
        == "ingress-nginx"
        and peer.get("podSelector", {}).get("matchLabels", {}).get("app.kubernetes.io/name")
        == "ingress-nginx"
        and {port["port"] for port in rule["ports"]} == {443}
        for rule in policy["spec"]["egress"]
        for peer in rule.get("to", [])
    )


def test_jellyfin_bootstrap_refreshes_a_stale_channel_lineup() -> None:
    root = ROOT / "playbooks/argocd/applications/media/jellyfin"
    lineups_match = load_jellyfin_bootstrap_function("lineups_match")

    dispatcharr = [
        {"GuideName": "25 РЕГИОН", "GuideNumber": "3"},
        {"GuideName": "Телемикс", "GuideNumber": "4"},
        {"GuideName": "Infinite Slop", "GuideNumber": "90"},
    ]
    stale = [
        {"Name": "Телемикс", "Number": "3"},
        {"Name": "25 РЕГИОН", "Number": "4"},
        {"Name": "Infinite Slop", "Number": "5"},
    ]
    current = [
        {"Name": "25 РЕГИОН", "Number": "3"},
        {"Name": "Телемикс", "Number": "4"},
        {"Name": "Infinite Slop", "Number": "90"},
    ]
    assert not lineups_match(dispatcharr, stale)
    assert lineups_match(dispatcharr, current)
    job = yaml.safe_load((root / "bootstrap-job.yaml").read_text())
    assert job["spec"]["activeDeadlineSeconds"] >= 900


def test_jellyfin_refreshes_the_guide_when_channel_artwork_is_missing() -> None:
    source = (ROOT / "playbooks/argocd/applications/media/jellyfin/bootstrap.py").read_text()
    functions = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"lineups_match", "guide_refresh_required"}
    ]
    namespace = {}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "bootstrap.py", "exec"), namespace)
    refresh_required = namespace["guide_refresh_required"]
    dispatcharr = [{"GuideName": "ОТВ Прим", "GuideNumber": "1"}]
    channel = {"Name": "ОТВ Прим", "Number": "1"}

    assert refresh_required(dispatcharr, [{**channel, "ImageTags": {}}])
    assert not refresh_required(
        dispatcharr,
        [{**channel, "ImageTags": {"Primary": "image-tag"}}],
    )


def test_jellyfin_starts_guide_refresh_by_task_id() -> None:
    source = (ROOT / "playbooks/argocd/applications/media/jellyfin/bootstrap.py").read_text()
    tree = ast.parse(source)
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"scheduled_task", "refresh_guide"}
    ]
    starts = iter(["old", "new"])
    started = []

    def fake_call(method, path, body=None, token=None):
        if method == "POST":
            started.append(path)
            return None
        return [
            {
                "Id": "refresh-guide-id",
                "Key": "RefreshGuide",
                "State": "Idle",
                "LastExecutionResult": {
                    "StartTimeUtc": next(starts),
                    "Status": "Completed",
                },
            }
        ]

    class FakeTime:
        now = 0

        @classmethod
        def monotonic(cls):
            cls.now += 1
            return cls.now

        @staticmethod
        def sleep(_seconds):
            pass

    namespace = {"call": fake_call, "time": FakeTime}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "bootstrap.py", "exec"), namespace)
    namespace["refresh_guide"]("token", timeout=10)

    assert started == ["/ScheduledTasks/Running/refresh-guide-id"]


def test_authentik_declares_jellyfin_oidc_and_live_tv_copies_its_secret() -> None:
    blueprint = (
        ROOT / "playbooks/argocd/applications/security/authentik/blueprints/native-apps.yaml"
    ).read_text()
    assert "Jellyfin" in blueprint
    assert "JELLYFIN_OIDC_CLIENT_SECRET" in blueprint
    assert "https://tv.soyspray.vip/sso/OID/redirect/authentik" in blueprint
    tasks = (ROOT / "roles/apps/live_tv/tasks/enabled.yml").read_text()
    assert "namespace: authentik" in tasks
    assert "JELLYFIN_OIDC_CLIENT_SECRET" in tasks


@pytest.mark.parametrize("name", ("media-helper", "dispatcharr", "jellyfin"))
def test_media_network_policies_allow_nodelocal_dns(name: str) -> None:
    policy = yaml.safe_load(
        (ROOT / f"playbooks/argocd/applications/media/{name}/network-policy.yaml").read_text()
    )
    cidrs = {
        peer["ipBlock"]["cidr"]
        for rule in policy["spec"]["egress"]
        for peer in rule.get("to", [])
        if "ipBlock" in peer
    }
    assert "169.254.25.10/32" in cidrs


def test_media_helper_cannot_read_the_dispatcharr_lineup() -> None:
    policy = yaml.safe_load((HELPER / "network-policy.yaml").read_text())
    selectors = [
        peer.get("podSelector", {}).get("matchLabels", {})
        for rule in policy["spec"]["egress"]
        for peer in rule.get("to", [])
    ]
    assert {"app": "dispatcharr"} not in selectors


def test_jellyfin_can_read_media_helper_without_reverse_control_access() -> None:
    helper = yaml.safe_load((HELPER / "network-policy.yaml").read_text())
    helper_ingress = [
        peer.get("podSelector", {}).get("matchLabels", {})
        for rule in helper["spec"]["ingress"]
        for peer in rule.get("from", [])
    ]
    helper_egress = [
        peer.get("podSelector", {}).get("matchLabels", {})
        for rule in helper["spec"]["egress"]
        for peer in rule.get("to", [])
    ]
    jellyfin = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/jellyfin/network-policy.yaml").read_text()
    )
    jellyfin_ingress = [
        peer.get("podSelector", {}).get("matchLabels", {})
        for rule in jellyfin["spec"]["ingress"]
        for peer in rule.get("from", [])
    ]
    assert {"app": "jellyfin"} in helper_ingress
    assert {"app": "jellyfin"} not in helper_egress
    assert {"app": "media-helper"} not in jellyfin_ingress


def test_dispatcharr_keeps_the_upstream_entrypoint_capabilities() -> None:
    deployment = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/dispatcharr/deployment.yaml").read_text()
    )
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert "securityContext" not in container


def test_dispatcharr_reconcile_can_reach_dispatcharr_and_has_a_deadline() -> None:
    policy = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/dispatcharr/network-policy.yaml").read_text()
    )
    selectors = [
        peer.get("podSelector", {}).get("matchLabels", {})
        for rule in policy["spec"]["ingress"]
        for peer in rule["from"]
    ]
    assert {"job-name": "dispatcharr-reconcile"} in selectors
    assert {"job-name": "jellyfin-bootstrap"} in selectors
    job = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/dispatcharr/reconcile-job.yaml").read_text()
    )
    assert job["spec"]["activeDeadlineSeconds"] == 600
    reconcile = (ROOT / "playbooks/argocd/applications/media/dispatcharr/reconcile.py").read_text()
    assert '"/core/settings/"' in reconcile
    assert '"default_stream_profile": profile["id"]' not in reconcile
    assert '"auto_enable_new_groups_live": True' in reconcile
    assert "request(f\"/m3u/refresh/{account['id']}/\"" in reconcile
    assert '"auto_channel_sync": True' not in reconcile
    assert '"auto_channel_sync": False' in reconcile
    assert "Dispatcharr did not assign a group" in reconcile
    assert "Dispatcharr did not publish the managed lineup" in reconcile
    assert 'request("", base=CATALOG_URL, timeout=90)' in reconcile


def test_dispatcharr_reconcile_is_import_safe_and_tunes_live_relays() -> None:
    source = RECONCILE.read_text()
    assert 'if __name__ == "__main__":' in source
    assert '"channel_shutdown_delay": 15' in source
    assert '"new_client_behind_seconds": 20' in source
    assert '"m3u_hash_key": "url"' not in source
    assert "Dispatcharr must use URL stream identity" in source
    assert "--plugin-dir /opt/streamlink-plugins" in source
    assert "--stream-segment-threads 2" in source
    assert "720p50,720p,480p50,480p,best" in source


@pytest.mark.parametrize(
    ("source_type", "expected_profile_id"),
    [("direct_hls", 1), ("streamlink_page", 7)],
)
def test_dispatcharr_reconcile_owns_only_managed_auto_channels(
    monkeypatch, source_type: str, expected_profile_id: int
) -> None:
    reconcile = load_reconcile()
    streams = [
        {
            "id": 1,
            "url": "https://example.test/live.m3u8",
            "tvg_id": "live",
            "m3u_account": 2,
            "is_stale": False,
        },
        {
            "id": 2,
            "url": "https://example.test/old.m3u8",
            "tvg_id": "old",
            "m3u_account": 2,
            "is_stale": True,
        },
        {
            "id": 3,
            "url": "https://other.test/old.m3u8",
            "tvg_id": "other",
            "m3u_account": 99,
            "is_stale": True,
        },
    ]
    channels = [
        {"id": 10, "auto_created": True, "auto_created_by": 2, "streams": [1, 4]},
        {"id": 11, "auto_created": True, "auto_created_by": 2, "streams": [2]},
        {"id": 9, "auto_created": False, "auto_created_by": None, "streams": [1, 2]},
        {"id": 13, "auto_created": True, "auto_created_by": 99, "streams": [3]},
    ]
    calls = []

    def rows(path, _token):
        return streams if path.startswith("/channels/streams/") else channels

    def request(path, method="GET", payload=None, token=None, base=reconcile.BASE, timeout=30):
        calls.append((path, method, payload, token, base))
        return {}

    monkeypatch.setattr(reconcile, "rows", rows)
    monkeypatch.setattr(reconcile, "request", request)
    reconcile.reconcile_channels(
        {
            "channels": [
                {
                    "slug": "live",
                    "number": 1,
                    "name": "Live",
                    "enabled": True,
                    "delivery": "dispatcharr",
                    "sources": [{"type": source_type, "url": "https://example.test/live.m3u8"}],
                    "guide": {"id": "live"},
                }
            ]
        },
        {"id": 2},
        "token",
        profile_ids={"direct_hls": 1, "streamlink_page": 7},
    )

    patched = [path for path, method, *_ in calls if method == "PATCH"]
    deleted = [path for path, method, *_ in calls if method == "DELETE"]
    assert patched == ["/channels/channels/10/"]
    patch_payload = next(payload for _, method, payload, *_ in calls if method == "PATCH")
    assert patch_payload["streams"] == [1, 4]
    assert patch_payload["override"] == {
        "name": "Live",
        "channel_number": 1,
        "tvg_id": "live",
        "stream_profile_id": expected_profile_id,
    }
    assert deleted == ["/channels/channels/11/"]


def test_dispatcharr_group_sync_preserves_settings_and_disables_empty_groups(
    monkeypatch,
) -> None:
    reconcile = load_reconcile()
    calls = []
    account = {
        "id": 2,
        "channel_groups": [
            {
                "channel_group": 10,
                "enabled": False,
                "auto_channel_sync": True,
                "auto_sync_channel_start": 20,
                "auto_sync_channel_end": 29,
                "custom_properties": {"stream_profile_id": 99},
                "stream_count": 0,
            },
            {
                "channel_group": 11,
                "enabled": True,
                "auto_channel_sync": False,
                "auto_sync_channel_start": 30,
                "auto_sync_channel_end": 39,
                "custom_properties": {"filter": "keep"},
                "stream_count": 2,
            },
        ],
    }

    def request(path, method="GET", payload=None, token=None, base=reconcile.BASE, timeout=30):
        calls.append((path, method, payload, token, base))
        return {}

    monkeypatch.setattr(reconcile, "request", request)
    reconcile.disable_group_sync(account, "token")

    disabled = calls[0][2]["group_settings"]
    assert disabled == [
        {
            "channel_group": 10,
            "enabled": False,
            "auto_channel_sync": False,
            "auto_sync_channel_start": 20,
            "auto_sync_channel_end": 29,
            "custom_properties": {"stream_profile_id": 99},
        },
        {
            "channel_group": 11,
            "enabled": True,
            "auto_channel_sync": False,
            "auto_sync_channel_start": 30,
            "auto_sync_channel_end": 39,
            "custom_properties": {"filter": "keep"},
        },
    ]


def test_dispatcharr_rejects_an_incompatible_global_stream_identity() -> None:
    reconcile = load_reconcile()
    reconcile.require_url_hash({"value": {"m3u_hash_key": "url"}})
    with pytest.raises(RuntimeError, match="must use URL stream identity"):
        reconcile.require_url_hash({"value": {"m3u_hash_key": "name"}})


def test_dispatcharr_restores_fallback_after_all_managed_sources_change(monkeypatch) -> None:
    reconcile = load_reconcile()
    catalog = {
        "channels": [
            {
                "slug": "live",
                "number": 1,
                "name": "Live",
                "enabled": True,
                "delivery": "dispatcharr",
                "sources": [{"type": "direct_hls", "url": "https://new.test/live.m3u8"}],
                "guide": {"id": "new-live-id"},
            }
        ]
    }
    streams = [
        {
            "id": 2,
            "url": "https://new.test/live.m3u8",
            "tvg_id": "new-live-id",
            "m3u_account": 2,
            "is_stale": False,
        },
        {
            "id": 1,
            "url": "https://old.test/live.m3u8",
            "tvg_id": "old-live-id",
            "m3u_account": 2,
            "is_stale": True,
        },
    ]
    channels = [
        {
            "id": 20,
            "auto_created": True,
            "auto_created_by": 2,
            "effective_name": "Live",
            "effective_tvg_id": "old-live-id",
            "streams": [1, 99],
        }
    ]
    calls = []

    def rows(path, _token):
        return streams if path.startswith("/channels/streams/") else channels

    def request(path, method="GET", payload=None, token=None, base=reconcile.BASE, timeout=30):
        calls.append((path, method, payload, token, base))
        return {}

    monkeypatch.setattr(reconcile, "rows", rows)
    monkeypatch.setattr(reconcile, "request", request)
    reconcile.reconcile_channels(
        catalog,
        {"id": 2},
        "token",
        profile_ids={"direct_hls": 1, "streamlink_page": 7},
    )
    patch = next(payload for _, method, payload, *_ in calls if method == "PATCH")
    assert patch["streams"] == [2, 99]
    assert patch["override"]["stream_profile_id"] == 1


def test_dispatcharr_creates_a_missing_owned_channel(monkeypatch) -> None:
    reconcile = load_reconcile()
    catalog = {
        "channels": [
            {
                "slug": "live",
                "number": 1,
                "name": "Live",
                "enabled": True,
                "delivery": "dispatcharr",
                "sources": [{"type": "direct_hls", "url": "https://new.test/live.m3u8"}],
                "guide": {"id": "live-id"},
            }
        ]
    }
    stream = {
        "id": 2,
        "url": "https://new.test/live.m3u8",
        "tvg_id": "live-id",
        "m3u_account": 2,
        "channel_group": 12,
        "is_stale": False,
    }
    calls = []

    monkeypatch.setattr(
        reconcile,
        "rows",
        lambda path, _token: [stream] if path.startswith("/channels/streams/") else [],
    )

    def request(path, method="GET", payload=None, token=None, base=reconcile.BASE, timeout=30):
        calls.append((path, method, payload, token, base))
        return {"id": 20}

    monkeypatch.setattr(reconcile, "request", request)
    reconcile.reconcile_channels(
        catalog,
        {"id": 2},
        "token",
        profile_ids={"direct_hls": 1, "streamlink_page": 7},
    )

    path, method, payload, *_ = next(call for call in calls if call[1] == "POST")
    assert path == "/channels/channels/"
    assert method == "POST"
    assert payload == {
        "name": "Live",
        "channel_number": 1,
        "channel_group_id": 12,
        "tvg_id": "live-id",
        "streams": [2],
        "auto_created": True,
        "auto_created_by": 2,
        "override": {
            "name": "Live",
            "channel_number": 1,
            "tvg_id": "live-id",
            "stream_profile_id": 1,
        },
    }


def test_dispatcharr_lineup_requires_each_managed_identity_once() -> None:
    reconcile = load_reconcile()
    catalog = {
        "channels": [
            {
                "enabled": True,
                "delivery": "dispatcharr",
                "number": 1,
                "name": "One",
            },
            {
                "enabled": True,
                "delivery": "dispatcharr",
                "number": 2,
                "name": "Two",
            },
        ]
    }
    exact = [
        {"GuideNumber": "1", "GuideName": "One"},
        {"GuideNumber": "2", "GuideName": "Two"},
    ]
    assert reconcile.lineup_matches(catalog, exact)
    assert not reconcile.lineup_matches(catalog, exact + [{"GuideNumber": "3", "GuideName": "Two"}])
    assert not reconcile.lineup_matches(
        catalog,
        [{"GuideNumber": "1", "GuideName": "Two"}, {"GuideNumber": "2", "GuideName": "One"}],
    )


def test_dispatcharr_keeps_auto_sync_disabled(monkeypatch) -> None:
    reconcile = load_reconcile()
    events = []

    monkeypatch.setenv("DISPATCHARR_ADMIN_USER", "admin")
    monkeypatch.setenv("DISPATCHARR_ADMIN_PASSWORD", "secret")

    monkeypatch.setattr(reconcile, "initialize", lambda: None)
    monkeypatch.setattr(
        reconcile,
        "request",
        lambda path, method="GET", payload=None, token=None, base=reconcile.BASE, timeout=30: (
            {"access": "token"}
            if path == "/accounts/token/"
            else {"id": 2, "channel_groups": [{"channel_group": 1, "stream_count": 1}]}
        ),
    )
    monkeypatch.setattr(
        reconcile,
        "rows",
        lambda path, _token: (
            [
                {
                    "id": 1,
                    "key": "stream_settings",
                    "value": {"m3u_hash_key": "url"},
                },
                {"id": 2, "key": "proxy_settings", "value": {}},
            ]
            if path == "/core/settings/"
            else [{"id": 1, "name": "ffmpeg", "locked": True}]
            if path == "/core/streamprofiles/"
            else []
        ),
    )
    monkeypatch.setattr(
        reconcile,
        "upsert",
        lambda path, name, payload, token: (
            {"id": 7}
            if path == "/core/streamprofiles/"
            else {
                "id": 2,
                "channel_groups": [{"channel_group": 1, "stream_count": 1}],
            }
        ),
    )

    def refresh(account, token):
        events.append("refresh")
        return account

    monkeypatch.setattr(reconcile, "refresh_account", refresh)
    monkeypatch.setattr(
        reconcile,
        "disable_group_sync",
        lambda account, token: events.append("disable"),
    )

    def fail_reconcile(catalog, account, token, profile_ids):
        events.append(("reconcile", profile_ids))
        raise RuntimeError("broken catalog")

    monkeypatch.setattr(reconcile, "reconcile_channels", fail_reconcile)

    with pytest.raises(RuntimeError, match="broken catalog"):
        reconcile.main()
    assert events == [
        "disable",
        "refresh",
        "disable",
        ("reconcile", {"direct_hls": 1, "streamlink_page": 7}),
    ]


def test_dispatcharr_has_memory_for_four_relays() -> None:
    deployment = yaml.safe_load(
        (ROOT / "playbooks/argocd/applications/media/dispatcharr/deployment.yaml").read_text()
    )
    resources = deployment["spec"]["template"]["spec"]["containers"][0]["resources"]
    assert resources["limits"] == {"cpu": "2", "memory": "3Gi"}


def test_dispatcharr_overrides_okru_metadata_schema_for_live_pages() -> None:
    root = ROOT / "playbooks/argocd/applications/media/dispatcharr"
    plugin = (root / "okru.py").read_text()
    assert "validate.any(dict, validate.parse_json())" in plugin
    assert 'validate.optional("metadata"): validate.any(dict, str)' in plugin
    deployment = yaml.safe_load((root / "deployment.yaml").read_text())
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]
    mount = next(item for item in container["volumeMounts"] if item["name"] == "okru-plugin")
    assert mount == {
        "name": "okru-plugin",
        "mountPath": "/opt/streamlink-plugins",
        "readOnly": True,
    }
    kustomization = yaml.safe_load((root / "kustomization.yaml").read_text())
    generated = next(
        item for item in kustomization["configMapGenerator"] if item["name"] == "okru-plugin"
    )
    assert generated["files"] == ["okru.py"]
