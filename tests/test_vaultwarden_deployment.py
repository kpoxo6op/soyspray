from __future__ import annotations

import json
import re
import subprocess

import yaml
from conftest import ROOT, load_yaml

PACKAGE = "kubernetes/vaultwarden"
APPLICATION = "playbooks/argocd/applications/security/vaultwarden/vaultwarden-application.yaml"
PROJECT = "playbooks/argocd/applications/security/vaultwarden/vaultwarden-project.yaml"


def render_package() -> list[dict]:
    result = subprocess.run(
        ["kubectl", "kustomize", PACKAGE],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def resource(resources: list[dict], kind: str, name: str = "vaultwarden") -> dict:
    return next(
        item for item in resources if item["kind"] == kind and item["metadata"]["name"] == name
    )


def test_vaultwarden_uses_one_restricted_persistent_replica() -> None:
    resources = render_package()
    deployment = resource(resources, "Deployment")
    pvc = resource(resources, "PersistentVolumeClaim", "vaultwarden-data")
    pod = deployment["spec"]["template"]["spec"]
    server = pod["containers"][0]
    environment = {item["name"]: item["value"] for item in server["env"]}

    assert deployment["spec"]["replicas"] == 1
    assert deployment["spec"]["strategy"] == {"type": "Recreate"}
    assert pvc["spec"]["accessModes"] == ["ReadWriteOnce"]
    assert pvc["spec"]["storageClassName"] == "longhorn"
    assert pod["automountServiceAccountToken"] is False
    assert pod["enableServiceLinks"] is False
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert pod["securityContext"]["seccompProfile"] == {"type": "RuntimeDefault"}
    assert re.fullmatch(
        r"ghcr\.io/dani-garcia/vaultwarden:[^@]+@sha256:[0-9a-f]{64}",
        server["image"],
    )
    assert ":latest" not in server["image"]
    assert server["imagePullPolicy"] == "IfNotPresent"
    assert environment["SIGNUPS_ALLOWED"] == "false"
    assert environment["INVITATIONS_ALLOWED"] == "false"
    assert server["securityContext"]["allowPrivilegeEscalation"] is False
    assert server["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    assert server["securityContext"]["readOnlyRootFilesystem"] is True
    assert server["resources"]["requests"]
    assert server["resources"]["limits"]
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert server[probe]["httpGet"] == {"path": "/alive", "port": "http"}
    data_mount = next(mount for mount in server["volumeMounts"] if mount["name"] == "data")
    assert data_mount["mountPath"] == "/data"
    data_volume = next(volume for volume in pod["volumes"] if volume["name"] == "data")
    assert data_volume["persistentVolumeClaim"]["claimName"] == "vaultwarden-data"


def test_vaultwarden_has_private_nginx_tls_and_bounded_argocd_ownership() -> None:
    resources = render_package()
    ingress = resource(resources, "Ingress")
    annotations = ingress["metadata"]["annotations"]
    app = load_yaml(APPLICATION)
    project = load_yaml(PROJECT)

    assert ingress["spec"]["ingressClassName"] == "nginx"
    assert annotations["cert-manager.io/cluster-issuer"] == "letsencrypt-prod"
    assert "external-dns.alpha.kubernetes.io/hostname" not in annotations
    assert ingress["spec"]["tls"] == [
        {"hosts": ["vault.soyspray.vip"], "secretName": "vaultwarden-tls"}
    ]
    assert ingress["spec"]["rules"][0]["host"] == "vault.soyspray.vip"

    assert app["metadata"]["name"] == "vaultwarden"
    assert app["metadata"]["namespace"] == "argocd"
    assert app["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]
    assert app["spec"]["project"] == "vaultwarden"
    assert app["spec"]["source"] == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "HEAD",
        "path": PACKAGE,
    }
    assert app["spec"]["destination"] == {
        "server": "https://kubernetes.default.svc",
        "namespace": "vaultwarden",
    }
    assert app["spec"]["syncPolicy"]["automated"] == {"prune": True, "selfHeal": True}

    assert project["metadata"] == {"name": "vaultwarden", "namespace": "argocd"}
    assert project["spec"]["sourceRepos"] == ["https://github.com/kpoxo6op/soyspray.git"]
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "vaultwarden"}
    ]
    assert project["spec"]["clusterResourceWhitelist"] == [{"group": "", "kind": "Namespace"}]
    assert {
        (item["group"], item["kind"]) for item in project["spec"]["namespaceResourceWhitelist"]
    } == {
        ("", "PersistentVolumeClaim"),
        ("", "Service"),
        ("apps", "Deployment"),
        ("networking.k8s.io", "Ingress"),
    }
    assert "*" not in json.dumps(project)


def test_vaultwarden_role_and_make_target_manage_the_application_lifecycle() -> None:
    defaults = load_yaml("roles/apps/vaultwarden/defaults/main.yml")
    main = (ROOT / "roles/apps/vaultwarden/tasks/main.yml").read_text()
    enabled = (ROOT / "roles/apps/vaultwarden/tasks/enabled.yml").read_text()
    disabled = (ROOT / "roles/apps/vaultwarden/tasks/disabled.yml").read_text()
    playbook = load_yaml("playbooks/deploy-argocd-apps.yml")[0]
    makefile = (ROOT / "Makefile").read_text()

    assert defaults == {
        "vaultwarden_enabled": True,
        "vaultwarden_target_revision": "HEAD",
        "vaultwarden_agent_master_password_override": "",
    }
    assert "enabled.yml" in main
    assert "disabled.yml" in main
    assert "vaultwarden_enabled | bool" in main
    assert "vaultwarden-agent-bootstrap" in enabled
    assert "kubernetes.core.k8s_info" in enabled
    assert "b64decode" in enabled
    assert "vaultwarden_agent_master_password_override" in enabled
    assert "lookup('ansible.builtin.password', '/dev/null'" in enabled
    assert "no_log: true" in enabled
    assert "state: present" in enabled
    assert "vaultwarden_target_revision | string" in enabled
    assert enabled.index("vaultwarden-project.yaml") < enabled.index("vaultwarden-application.yaml")
    assert "state: present" not in disabled
    assert "lookup('file'" not in disabled
    assert "kubernetes.core.k8s_info" in disabled
    assert disabled.index("state: patched") < disabled.index("state: absent")
    assert "operation: null" in disabled
    assert "automated: null" in disabled
    assert "wait: true" in disabled
    assert disabled.index("kind: Application") < disabled.index("kind: AppProject")
    assert any(item["role"] == "apps/vaultwarden" for item in playbook["vars"]["argocd_app_roles"])

    assert "VAULTWARDEN_ENABLED ?= true" in makefile
    assert "VAULTWARDEN_REVISION ?= HEAD" in makefile
    assert PACKAGE in makefile
    assert "roles/apps/vaultwarden/tasks/*.yml" in makefile
    assert "roles/apps/vaultwarden/defaults/*.yml" in makefile
    assert "vaultwarden: go" in makefile
    assert "--tags vaultwarden" in makefile
    assert "vaultwarden_enabled=$(VAULTWARDEN_ENABLED)" in makefile
    assert "vaultwarden_target_revision=$(VAULTWARDEN_REVISION)" in makefile
