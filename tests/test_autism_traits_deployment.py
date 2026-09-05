from __future__ import annotations

import json
import subprocess

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from conftest import ROOT, load_yaml

try:
    from ansible.template import trust_as_template
except ImportError:

    def trust_as_template(value: str) -> str:
        """Keep compatibility with Ansible versions that trust strings by default."""
        return value


PACKAGE = "kubernetes/autism-traits"
APPLICATION = "playbooks/argocd/applications/web/autism-traits/autism-traits-application.yaml"
PROJECT = "playbooks/argocd/applications/web/autism-traits/autism-traits-project.yaml"
CLOUDFLARE_TUNNEL_ENDPOINTS = {
    "198.41.192.7/32",
    "198.41.192.27/32",
    "198.41.192.37/32",
    "198.41.192.47/32",
    "198.41.192.57/32",
    "198.41.192.67/32",
    "198.41.192.77/32",
    "198.41.192.107/32",
    "198.41.192.167/32",
    "198.41.192.227/32",
    "198.41.200.13/32",
    "198.41.200.23/32",
    "198.41.200.33/32",
    "198.41.200.43/32",
    "198.41.200.53/32",
    "198.41.200.63/32",
    "198.41.200.73/32",
    "198.41.200.113/32",
    "198.41.200.193/32",
    "198.41.200.233/32",
}
EXPECTED_SITE_PATHS = {
    "index.html",
    "assets/app.js",
    "assets/app.css",
    "images/bamboo-window.webp",
    "images/calm-sea.webp",
    "images/celestial-globe.webp",
    "images/hokusai-wave.webp",
    "images/irises.webp",
    "images/le-gray-wave.webp",
    "images/moonrise.webp",
    "images/old-trees.webp",
    "images/ottoman-calligraphy.webp",
    "images/oxbow.webp",
    "images/the-thinker.webp",
    "images/water-pitcher.webp",
    "images/wari-tunic.webp",
    "images/wheat-field.webp",
}


def render_package() -> list[dict]:
    result = subprocess.run(
        ["kubectl", "kustomize", PACKAGE],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def resource(
    resources: list[dict], kind: str, name: str | None = None, api_version: str | None = None
) -> dict:
    return next(
        item
        for item in resources
        if item["kind"] == kind
        and (name is None or item["metadata"]["name"] == name)
        and (api_version is None or item["apiVersion"] == api_version)
    )


def test_site_uses_the_selected_runtime_without_mutable_asset_overrides() -> None:
    resources = render_package()
    deployment = resource(resources, "Deployment", "autism-traits")
    pod = deployment["spec"]["template"]["spec"]
    if pod["containers"][0]["image"].startswith("ghcr.io/kpoxo6op/autism-traits@sha256:"):
        assert {volume["name"] for volume in pod["volumes"]} == {"tls", "tmp"}
        return
    configmaps = [item for item in resources if item["kind"] == "ConfigMap"]
    site_configmaps = [
        item for item in configmaps if item["metadata"]["name"].startswith("autism-traits-site-")
    ]
    image_configmaps = [
        item
        for item in site_configmaps
        if any(key.endswith(".webp") for key in item.get("binaryData", {}))
    ]

    assert len(image_configmaps) >= 4
    assert {
        key
        for item in image_configmaps
        for key in item.get("binaryData", {})
        if key.endswith(".webp")
    } == {path.removeprefix("images/") for path in EXPECTED_SITE_PATHS if path.endswith(".webp")}
    for item in site_configmaps:
        assert len(json.dumps(item, separators=(",", ":")).encode()) < 800 * 1024
        assert item["metadata"]["annotations"]["argocd.argoproj.io/sync-options"] == (
            "ServerSideApply=true"
        )

    pod_spec = deployment["spec"]["template"]["spec"]
    site_volume = next(volume for volume in pod_spec["volumes"] if volume["name"] == "site")
    site_sources = site_volume["projected"]["sources"]
    projected_names = {source["configMap"]["name"] for source in site_sources}
    projected_paths = {
        item["path"] for source in site_sources for item in source["configMap"]["items"]
    }
    dist = ROOT / PACKAGE / "app/dist"
    dist_paths = {str(path.relative_to(dist)) for path in dist.rglob("*") if path.is_file()}
    assert projected_names == {item["metadata"]["name"] for item in site_configmaps}
    assert projected_paths == EXPECTED_SITE_PATHS
    assert projected_paths == dist_paths

    web = pod_spec["containers"][0]
    site_mount = next(mount for mount in web["volumeMounts"] if mount["mountPath"] == "/site")
    assert site_mount["readOnly"] is True


def test_workload_is_restricted_and_observable() -> None:
    resources = render_package()
    deployment = resource(resources, "Deployment", "autism-traits")
    service = resource(resources, "Service")
    namespace = resource(resources, "Namespace")
    pod_spec = deployment["spec"]["template"]["spec"]
    web = pod_spec["containers"][0]

    labels = namespace["metadata"]["labels"]
    assert namespace["metadata"]["name"] == "autism-traits"
    assert labels["pod-security.kubernetes.io/enforce"] == "restricted"
    assert labels["pod-security.kubernetes.io/enforce-version"] == "v1.35"
    assert labels["pod-security.kubernetes.io/warn"] == "restricted"
    assert labels["pod-security.kubernetes.io/warn-version"] == "v1.35"

    assert pod_spec["automountServiceAccountToken"] is False
    assert pod_spec["enableServiceLinks"] is False
    assert pod_spec["securityContext"]["runAsNonRoot"] is True
    assert pod_spec["securityContext"]["fsGroup"] == 101
    assert pod_spec["securityContext"]["seccompProfile"] == {"type": "RuntimeDefault"}
    assert web["image"].startswith(
        ("nginxinc/nginx-unprivileged:", "ghcr.io/kpoxo6op/autism-traits@sha256:")
    )
    assert "@sha256:" in web["image"]
    assert web["imagePullPolicy"] == "IfNotPresent"
    assert web["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
        "readOnlyRootFilesystem": True,
        "runAsGroup": 101,
        "runAsUser": 101,
    }
    assert web["resources"]["requests"]
    assert web["resources"]["limits"]
    assert web["startupProbe"]["httpGet"] == {"path": "/index.html", "port": "http"}
    assert web["readinessProbe"]["httpGet"] == {"path": "/index.html", "port": "http"}
    assert web["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert service["spec"]["ports"] == [
        {"name": "http", "port": 80, "targetPort": "http"},
        {"name": "https", "port": 443, "targetPort": "https"},
    ]
    assert {port["name"] for port in web["ports"]} == {"http", "https"}
    tls_mount = next(mount for mount in web["volumeMounts"] if mount["name"] == "tls")
    assert tls_mount == {"name": "tls", "mountPath": "/tls", "readOnly": True}
    tls_volume = next(volume for volume in pod_spec["volumes"] if volume["name"] == "tls")
    assert tls_volume == {
        "name": "tls",
        "secret": {"secretName": "autism-traits-tls", "defaultMode": 0o440},
    }


def test_cloudflared_is_a_separate_hardened_connector() -> None:
    deployment = resource(render_package(), "Deployment", "autism-traits-cloudflared")
    pod_spec = deployment["spec"]["template"]["spec"]
    connector = pod_spec["containers"][0]

    assert deployment["spec"]["replicas"] == 2
    assert deployment["spec"]["selector"]["matchLabels"] == {
        "app.kubernetes.io/name": "autism-traits-cloudflared"
    }
    assert pod_spec["automountServiceAccountToken"] is False
    assert pod_spec["enableServiceLinks"] is False
    assert pod_spec.get("hostNetwork") is not True
    assert pod_spec["securityContext"] == {
        "runAsNonRoot": True,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    assert connector["image"] == (
        "cloudflare/cloudflared:2026.7.3@"
        "sha256:e39ee8da81ad5e05d77f38d2f51c60ca51bf2a8450ac3abab50c17fdb91d91bf"
    )
    assert connector["imagePullPolicy"] == "IfNotPresent"
    assert connector["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
        "readOnlyRootFilesystem": True,
        "runAsGroup": 65532,
        "runAsUser": 65532,
    }
    assert connector["resources"]["requests"]
    assert connector["resources"]["limits"]
    assert connector["env"] == [
        {
            "name": "TUNNEL_TOKEN",
            "valueFrom": {
                "secretKeyRef": {"name": "autism-traits-cloudflared-token", "key": "token"}
            },
        }
    ]
    args = connector["args"]
    assert args == [
        "tunnel",
        "--no-autoupdate",
        "--loglevel",
        "error",
        "--metrics",
        "0.0.0.0:2000",
        "run",
    ]
    assert connector["readinessProbe"]["httpGet"] == {"path": "/ready", "port": "metrics"}
    assert connector["livenessProbe"]["httpGet"] == {"path": "/ready", "port": "metrics"}


def test_cloudflared_closes_the_local_ipvs_service_path() -> None:
    resources = render_package()
    service = resource(resources, "Service", "autism-traits")
    host_policy = resource(
        resources,
        "GlobalNetworkPolicy",
        "autism-traits-cloudflared-host-boundary",
        "crd.projectcalico.org/v1",
    )
    host_endpoints = {
        item["metadata"]["name"]: item
        for item in resources
        if item.get("apiVersion") == "crd.projectcalico.org/v1"
        and item.get("kind") == "HostEndpoint"
    }

    assert service["spec"]["clusterIP"] == "10.233.23.96"
    assert service["spec"]["clusterIPs"] == ["10.233.23.96"]
    assert host_endpoints.keys() == {
        "autism-traits-node-0-host-boundary",
        "autism-traits-node-1-host-boundary",
        "autism-traits-node-2-host-boundary",
    }
    for index, endpoint in enumerate(host_endpoints.values()):
        assert endpoint["metadata"].get("namespace") is None
        assert endpoint["metadata"]["labels"]["autism-traits-host-boundary"] == "true"
        assert endpoint["spec"] == {
            "node": f"node-{index}",
            "interfaceName": "*",
            "expectedIPs": [f"192.168.20.{10 + index}"],
            "profiles": ["projectcalico-default-allow"],
        }

    assert host_policy["metadata"].get("namespace") is None
    assert host_policy["spec"] == {
        "order": 10,
        "selector": "autism-traits-host-boundary == 'true'",
        "preDNAT": True,
        "applyOnForward": True,
        "types": ["Ingress"],
        "ingress": [
            {
                "action": "Deny",
                "source": {
                    "namespaceSelector": "projectcalico.org/name == 'autism-traits'",
                    "selector": "autism-traits-component == 'cloudflared'",
                },
                "destination": {
                    "nets": [
                        "10.233.0.0/18",
                        "10.233.64.0/18",
                        "192.168.20.0/24",
                    ],
                    "notNets": ["10.233.23.96/32"],
                    "notSelector": (
                        "projectcalico.org/namespace == 'autism-traits' && "
                        "autism-traits-component == 'web'"
                    ),
                },
            }
        ],
    }


def test_private_ingress_keeps_tls_but_does_not_own_public_dns() -> None:
    ingress = resource(render_package(), "Ingress")
    annotations = ingress["metadata"]["annotations"]

    assert ingress["spec"]["ingressClassName"] == "nginx"
    assert annotations["cert-manager.io/cluster-issuer"] == "letsencrypt-prod"
    assert "external-dns.alpha.kubernetes.io/hostname" not in annotations
    assert ingress["spec"]["tls"] == [
        {"hosts": ["autism.soyspray.vip"], "secretName": "autism-traits-tls"}
    ]
    assert ingress["spec"]["rules"][0]["host"] == "autism.soyspray.vip"


def test_namespace_and_web_have_default_deny_boundaries() -> None:
    resources = render_package()
    default_deny = resource(
        resources, "NetworkPolicy", "autism-traits-default-deny", "networking.k8s.io/v1"
    )["spec"]
    web_policy = resource(resources, "NetworkPolicy", "autism-traits-web", "networking.k8s.io/v1")[
        "spec"
    ]

    assert default_deny == {
        "podSelector": {},
        "policyTypes": ["Ingress", "Egress"],
    }
    assert web_policy["podSelector"] == {"matchLabels": {"autism-traits-component": "web"}}
    assert web_policy["policyTypes"] == ["Ingress", "Egress"]
    assert web_policy["egress"] == []
    assert web_policy["ingress"] == [
        {
            "from": [{"podSelector": {"matchLabels": {"autism-traits-component": "cloudflared"}}}],
            "ports": [{"protocol": "TCP", "port": 8443}],
        },
        {
            "from": [
                {
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": "ingress-nginx"}
                    },
                    "podSelector": {"matchLabels": {"app.kubernetes.io/name": "ingress-nginx"}},
                }
            ],
            "ports": [{"protocol": "TCP", "port": 8080}],
        },
    ]


def test_cloudflared_egress_is_only_dns_web_and_exact_cloudflare_endpoints() -> None:
    resources = render_package()
    policy = resource(
        resources, "NetworkPolicy", "autism-traits-cloudflared", "networking.k8s.io/v1"
    )["spec"]

    assert policy["podSelector"] == {"matchLabels": {"autism-traits-component": "cloudflared"}}
    assert policy["policyTypes"] == ["Egress"]
    assert policy.get("ingress") is None
    assert policy["egress"][0] == {
        "to": [{"ipBlock": {"cidr": "169.254.25.10/32"}}],
        "ports": [
            {"protocol": "UDP", "port": 53},
            {"protocol": "TCP", "port": 53},
        ],
    }
    assert policy["egress"][1] == {
        "to": [{"podSelector": {"matchLabels": {"autism-traits-component": "web"}}}],
        "ports": [{"protocol": "TCP", "port": 8443}],
    }
    endpoint_rule = policy["egress"][2]
    assert {item["ipBlock"]["cidr"] for item in endpoint_rule["to"]} == (
        CLOUDFLARE_TUNNEL_ENDPOINTS
    )
    assert endpoint_rule["ports"] == [
        {"protocol": "TCP", "port": 7844},
        {"protocol": "UDP", "port": 7844},
    ]
    rendered = json.dumps(policy)
    for forbidden in ("0.0.0.0/0", "10.233.0.0", "192.168.20.0"):
        assert forbidden not in rendered


def test_calico_policy_closes_the_node_and_api_exception() -> None:
    policy = resource(
        render_package(),
        "NetworkPolicy",
        "autism-traits-cloudflared-boundary",
        "crd.projectcalico.org/v1",
    )["spec"]

    assert policy["order"] == 10
    assert policy["selector"] == "autism-traits-component == 'cloudflared'"
    assert policy["types"] == ["Egress"]
    assert policy["egress"][-1] == {"action": "Deny"}
    assert any(
        rule.get("action") == "Allow"
        and rule.get("destination", {}).get("nets") == ["169.254.25.10/32"]
        and rule.get("destination", {}).get("ports") == [53]
        for rule in policy["egress"]
    )
    assert any(
        rule.get("action") == "Allow"
        and rule.get("destination", {}).get("selector") == "autism-traits-component == 'web'"
        and rule.get("destination", {}).get("ports") == [8443]
        for rule in policy["egress"]
    )
    endpoint_nets = {
        cidr
        for rule in policy["egress"]
        for cidr in rule.get("destination", {}).get("nets", [])
        if rule.get("destination", {}).get("ports") == [7844]
    }
    assert endpoint_nets == CLOUDFLARE_TUNNEL_ENDPOINTS
    rendered = json.dumps(policy)
    for forbidden in ("0.0.0.0/0", "10.233.0.1", "192.168.20.0/24"):
        assert forbidden not in rendered


def test_calico_policy_makes_web_egress_genuinely_zero() -> None:
    policy = resource(
        render_package(),
        "NetworkPolicy",
        "autism-traits-web-zero-egress",
        "crd.projectcalico.org/v1",
    )["spec"]

    assert policy == {
        "order": 10,
        "selector": "autism-traits-component == 'web'",
        "types": ["Egress"],
        "egress": [{"action": "Deny"}],
    }


def test_nginx_uses_a_strict_local_only_csp_and_security_headers() -> None:
    config = (ROOT / PACKAGE / "config/nginx.conf").read_text()

    assert (
        "Content-Security-Policy \"default-src 'self'; base-uri 'none'; connect-src 'none'; "
        "font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self'; "
        "manifest-src 'self'; media-src 'none'; object-src 'none'; script-src 'self'; "
        "style-src 'self'; worker-src 'none'\" always;"
    ) in config
    assert "'unsafe-inline'" not in config
    assert "'unsafe-eval'" not in config
    assert "https:" not in config
    assert "listen 8443 ssl;" in config
    assert "ssl_certificate /tls/tls.crt;" in config
    assert "ssl_certificate_key /tls/tls.key;" in config
    assert "noTLSVerify" not in config
    assert "access_log off;" in config
    assert "access_log /dev/stdout" not in config
    assert "error_log /dev/stderr emerg;" in config
    assert "if ($request_method !~ ^(GET|HEAD)$)" in config
    assert "return 405;" in config
    for header in (
        "Cross-Origin-Opener-Policy",
        "Cross-Origin-Resource-Policy",
        "Permissions-Policy",
        "Referrer-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
    ):
        assert f"add_header {header} " in config


def test_argocd_application_uses_a_restricted_project() -> None:
    app = load_yaml(APPLICATION)
    project = load_yaml(PROJECT)

    assert app["metadata"]["name"] == "autism-traits"
    assert app["metadata"]["namespace"] == "argocd"
    assert app["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]
    assert app["spec"]["project"] == "autism-traits"
    assert app["spec"]["source"] == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "HEAD",
        "path": PACKAGE,
    }
    assert app["spec"]["destination"] == {
        "server": "https://kubernetes.default.svc",
        "namespace": "autism-traits",
    }
    assert app["spec"]["syncPolicy"]["automated"] == {"prune": True, "selfHeal": True}
    assert "CreateNamespace=true" in app["spec"]["syncPolicy"]["syncOptions"]
    assert "ServerSideApply=true" not in app["spec"]["syncPolicy"]["syncOptions"]
    namespace_labels = app["spec"]["syncPolicy"]["managedNamespaceMetadata"]["labels"]
    assert namespace_labels["pod-security.kubernetes.io/enforce"] == "restricted"
    assert namespace_labels["pod-security.kubernetes.io/enforce-version"] == "v1.35"

    assert project["metadata"] == {"name": "autism-traits", "namespace": "argocd"}
    assert project["spec"]["sourceRepos"] == ["https://github.com/kpoxo6op/soyspray.git"]
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "autism-traits"}
    ]
    assert project["spec"]["clusterResourceWhitelist"] == [
        {"group": "", "kind": "Namespace"},
        {"group": "crd.projectcalico.org", "kind": "GlobalNetworkPolicy"},
        {"group": "crd.projectcalico.org", "kind": "HostEndpoint"},
    ]
    assert project["spec"]["namespaceResourceWhitelist"] == [
        {"group": "", "kind": "ConfigMap"},
        {"group": "", "kind": "Service"},
        {"group": "apps", "kind": "Deployment"},
        {"group": "networking.k8s.io", "kind": "Ingress"},
        {"group": "networking.k8s.io", "kind": "NetworkPolicy"},
        {"group": "crd.projectcalico.org", "kind": "NetworkPolicy"},
    ]
    assert "*" not in json.dumps(project)


def test_application_has_no_browser_storage_or_data_transmission() -> None:
    source = "\n".join(
        path.read_text()
        for path in (ROOT / "apps/autism-traits/app/src").rglob("*")
        if path.is_file()
    )

    assert "localStorage.getItem" not in source
    assert "localStorage.setItem" not in source
    assert 'localStorage.removeItem("autism-traits-assessment:v1")' in source
    assert "sessionStorage" not in source
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source
    assert "navigator.sendBeacon" not in source
    assert "connect-src 'none'" in (ROOT / PACKAGE / "config/nginx.conf").read_text()
    assert "not transmitted or retained" in source
    assert "Cloudflare may process connection metadata" in source


def test_role_defaults_enable_the_site_and_propagate_revision() -> None:
    defaults = load_yaml("roles/apps/autism-traits/defaults/main.yml")
    enabled = (ROOT / "roles/apps/autism-traits/tasks/enabled.yml").read_text()

    assert defaults == {
        "autism_traits_enabled": True,
        "autism_traits_target_revision": "HEAD",
    }
    assert "state: present" in enabled
    assert "autism_traits_target_revision" in enabled
    assert "name: app-secret" in enabled
    assert "AUTISM_TRAITS_CLOUDFLARED_TOKEN" in enabled
    assert "autism-traits-cloudflared-token" in enabled
    assert "autism-traits-project.yaml" in enabled
    assert enabled.index("autism-traits-project.yaml") < enabled.index(
        "autism-traits-application.yaml"
    )


@pytest.mark.parametrize("revision", ("feat/autism-assessment", "true", "null", "2026"))
def test_role_renders_every_valid_revision_as_a_string(revision: str) -> None:
    enabled = load_yaml("roles/apps/autism-traits/tasks/enabled.yml")
    application_task = next(
        task for task in enabled if "autism-traits-application.yaml" in json.dumps(task)
    )
    expression = application_task["kubernetes.core.k8s"]["definition"]
    templar = Templar(
        loader=DataLoader(),
        variables={
            "playbook_dir": str(ROOT / "playbooks"),
            "autism_traits_target_revision": revision,
        },
    )
    rendered = templar.template(trust_as_template(expression))
    app = yaml.safe_load(rendered) if isinstance(rendered, str) else rendered

    assert app["spec"]["source"]["targetRevision"] == revision


def test_role_quiesces_the_live_application_before_disabling_it() -> None:
    main = (ROOT / "roles/apps/autism-traits/tasks/main.yml").read_text()
    disabled = (ROOT / "roles/apps/autism-traits/tasks/disabled.yml").read_text()

    assert "enabled.yml" in main
    assert "disabled.yml" in main
    assert "autism_traits_enabled | bool" in main
    assert "state: present" not in disabled
    assert "lookup('file'" not in disabled
    assert "kubernetes.core.k8s_info" in disabled
    assert disabled.index("state: patched") < disabled.index("state: absent")
    assert "operation: null" in disabled
    assert "automated: null" in disabled
    assert "when:" in disabled
    assert "name: autism-traits" in disabled
    assert "namespace: argocd" in disabled
    assert "wait: true" in disabled
    assert "kind: Secret" in disabled
    assert "name: autism-traits-cloudflared-token" in disabled
    assert "kind: AppProject" in disabled
    assert disabled.index("Remove the autism traits Cloudflare Tunnel token") < disabled.index(
        "Remove the autism traits Argo application"
    )
    assert disabled.index("Remove the autism traits Argo project") > disabled.index(
        "Remove the autism traits Argo application"
    )


def test_operator_and_ci_paths_include_the_site_without_weakening_python_checks() -> None:
    makefile = (ROOT / "Makefile").read_text()
    playbook = load_yaml("playbooks/deploy-argocd-apps.yml")[0]
    workflow = load_yaml(".github/workflows/ci.yml")
    steps = workflow["jobs"]["autism"]["steps"]
    shared_steps = workflow["jobs"]["shared"]["steps"]
    runs = "\n".join(step.get("run", "") for step in steps)

    assert PACKAGE in makefile
    assert "cd $(AUTISM_TRAITS_APP) && npm ci" in makefile
    assert "autism-traits-check" in makefile
    assert "autism-traits: go" in makefile
    assert "--tags autism_traits" in makefile
    assert "autism_traits_target_revision=$(AUTISM_TRAITS_REVISION)" in makefile
    assert any(
        item["role"] == "apps/autism-traits" for item in playbook["vars"]["argocd_app_roles"]
    )

    node_step = next(
        step for step in steps if step.get("uses", "").startswith("actions/setup-node@")
    )
    assert str(node_step["with"]["node-version"]) == "22"
    assert "apps/autism-traits/app/package-lock.json" == node_step["with"]["cache-dependency-path"]
    assert "npm ci" in runs
    assert "npm run check" in runs
    assert "playwright install --with-deps chromium" in runs
    assert "npm run test:e2e" in runs
    assert any(step.get("uses") == "actions/setup-python@v6" for step in shared_steps)
    assert any(
        "make lint validate test PYTHON=python3" in step.get("run", "") for step in shared_steps
    )
