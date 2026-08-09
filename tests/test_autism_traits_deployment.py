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
EXPECTED_SITE_PATHS = {
    "index.html",
    "assets/app.js",
    "assets/app.css",
    "images/bamboo-window.webp",
    "images/calm-sea.webp",
    "images/hokusai-wave.webp",
    "images/irises.webp",
    "images/le-gray-wave.webp",
    "images/moonrise.webp",
    "images/old-trees.webp",
    "images/oxbow.webp",
    "images/water-pitcher.webp",
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


def resource(resources: list[dict], kind: str) -> dict:
    return next(item for item in resources if item["kind"] == kind)


def test_dist_is_projected_from_bounded_configmaps() -> None:
    resources = render_package()
    deployment = resource(resources, "Deployment")
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
    deployment = resource(resources, "Deployment")
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
    assert pod_spec["securityContext"]["runAsNonRoot"] is True
    assert pod_spec["securityContext"]["seccompProfile"] == {"type": "RuntimeDefault"}
    assert web["image"].startswith("nginxinc/nginx-unprivileged:")
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
    assert service["spec"]["ports"] == [{"name": "http", "port": 80, "targetPort": "http"}]


def test_ingress_has_dedicated_tls_and_external_dns() -> None:
    ingress = resource(render_package(), "Ingress")
    annotations = ingress["metadata"]["annotations"]

    assert ingress["spec"]["ingressClassName"] == "nginx"
    assert annotations["cert-manager.io/cluster-issuer"] == "letsencrypt-prod"
    assert annotations["external-dns.alpha.kubernetes.io/hostname"] == "autism.soyspray.vip"
    assert ingress["spec"]["tls"] == [
        {"hosts": ["autism.soyspray.vip"], "secretName": "autism-traits-tls"}
    ]
    assert ingress["spec"]["rules"][0]["host"] == "autism.soyspray.vip"


def test_network_policy_allows_only_ingress_nginx_and_no_egress() -> None:
    policy = resource(render_package(), "NetworkPolicy")["spec"]

    assert policy["policyTypes"] == ["Ingress", "Egress"]
    assert policy["egress"] == []
    assert policy["ingress"] == [
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
        }
    ]


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
    for header in (
        "Cross-Origin-Opener-Policy",
        "Cross-Origin-Resource-Policy",
        "Permissions-Policy",
        "Referrer-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
    ):
        assert f"add_header {header} " in config


def test_argocd_application_reconciles_head_in_the_default_project() -> None:
    app = load_yaml(APPLICATION)

    assert app["metadata"]["name"] == "autism-traits"
    assert app["metadata"]["namespace"] == "argocd"
    assert app["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]
    assert app["spec"]["project"] == "default"
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
    namespace_labels = app["spec"]["syncPolicy"]["managedNamespaceMetadata"]["labels"]
    assert namespace_labels["pod-security.kubernetes.io/enforce"] == "restricted"
    assert namespace_labels["pod-security.kubernetes.io/enforce-version"] == "v1.35"


def test_role_defaults_enable_the_site_and_propagate_revision() -> None:
    defaults = load_yaml("roles/apps/autism-traits/defaults/main.yml")
    enabled = (ROOT / "roles/apps/autism-traits/tasks/enabled.yml").read_text()

    assert defaults == {
        "autism_traits_enabled": True,
        "autism_traits_target_revision": "HEAD",
    }
    assert "state: present" in enabled
    assert "autism_traits_target_revision" in enabled


@pytest.mark.parametrize("revision", ("feat/autism-assessment", "true", "null", "2026"))
def test_role_renders_every_valid_revision_as_a_string(revision: str) -> None:
    enabled = load_yaml("roles/apps/autism-traits/tasks/enabled.yml")
    expression = enabled[0]["kubernetes.core.k8s"]["definition"]
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


def test_operator_and_ci_paths_include_the_site_without_weakening_python_checks() -> None:
    makefile = (ROOT / "Makefile").read_text()
    playbook = load_yaml("playbooks/deploy-argocd-apps.yml")[0]
    workflow = load_yaml(".github/workflows/ci.yml")
    steps = workflow["jobs"]["check"]["steps"]
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
    assert (
        "kubernetes/autism-traits/app/package-lock.json"
        == node_step["with"]["cache-dependency-path"]
    )
    assert "npm ci" in runs
    assert "npm run check" in runs
    assert "git diff --exit-code -- kubernetes/autism-traits/app/dist" in runs
    assert "git ls-files --others --exclude-standard" in runs
    assert "playwright install --with-deps chromium" in runs
    assert "npm run test:e2e" in runs
    assert any(step.get("uses") == "actions/setup-python@v6" for step in steps)
    assert "make check PYTHON=python3" in runs
