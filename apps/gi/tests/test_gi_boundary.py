"""Protect the private workspace boundary, access policy, and durable data.

These checks read the reviewed manifests only.  They never contact the cluster
and never contain a personal value, record, or export.
"""

import re
import subprocess
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/gi"
BLUEPRINTS = ROOT / "apps/authentik/manifests/blueprints"

DIGEST_IMAGE = re.compile(r"^ghcr\.io/kpoxo6op/gi-app@sha256:[0-9a-f]{64}$")
HOSTNAME = "gi.soyspray.vip"


class BlueprintLoader(yaml.SafeLoader):
    """Read Authentik blueprints, which use custom `!` tags.

    This mirrors `scripts/validate_yaml.py`: a custom scalar tag becomes its
    text and a custom sequence tag becomes the sequence, so `!KeyOf x` reads as
    the string `x` and `!Find [model, [key, value]]` reads as a nested list.
    """


def _tagged(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


BlueprintLoader.add_multi_constructor("!", _tagged)


def blueprint(name):
    return yaml.load((BLUEPRINTS / name).read_text(), Loader=BlueprintLoader)


def find_target(value):
    """Resolve a `!Find [authentik_core.group, [name, X]]` reference to X."""
    assert isinstance(value, list) and value[0] == "authentik_core.group", value
    pairs = value[1]
    assert pairs[0] == "name", pairs
    return pairs[1]


@lru_cache(maxsize=1)
def rendered():
    """Return the Application, its resources by kind, and the resource list."""
    application = yaml.safe_load((APP / "argocd/application.yaml").read_text())
    source = ROOT / application["spec"]["source"]["path"]
    resources = list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(source)], text=True)
        )
    )
    kinds = {}
    for item in resources:
        kinds.setdefault(item["kind"], []).append(item)
    return application, kinds, resources


def named(kind, name):
    return next(item for item in rendered()[1][kind] if item["metadata"]["name"] == name)


def test_application_is_pinned_to_the_public_repository_and_its_own_project():
    application, _, _ = rendered()
    assert application["spec"]["project"] == "gi"
    assert application["spec"]["source"] == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "main",
        "path": "apps/gi/manifests",
    }
    assert application["spec"]["destination"]["namespace"] == "gi"
    assert application["metadata"].get("finalizers", []) == []
    options = application["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
    assert "Prune=false" in options and "Delete=false" in options


def test_project_cannot_manage_anything_outside_its_namespace():
    application, _, _ = rendered()
    project = yaml.safe_load((APP / "argocd/project.yaml").read_text())
    assert project["metadata"]["name"] == application["spec"]["project"]
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "gi"}
    ]
    assert project["spec"]["sourceRepos"] == ["https://github.com/kpoxo6op/soyspray.git"]
    assert project["spec"]["clusterResourceWhitelist"] == [{"group": "", "kind": "Namespace"}]
    kinds = {
        (entry["group"], entry["kind"]) for entry in project["spec"]["namespaceResourceWhitelist"]
    }
    assert kinds == {
        ("", "ConfigMap"),
        ("", "PersistentVolumeClaim"),
        ("", "Service"),
        ("cert-manager.io", "Certificate"),
        ("apps", "Deployment"),
        ("networking.k8s.io", "Ingress"),
    }


def test_durable_resources_cannot_be_pruned_or_deleted_by_a_sync():
    _, kinds, _ = rendered()
    durable = kinds["Namespace"] + kinds["PersistentVolumeClaim"]
    assert durable, "the package must declare its own namespace and claims"
    for item in durable:
        options = item["metadata"]["annotations"]["argocd.argoproj.io/sync-options"]
        assert "Prune=false" in options, item["metadata"]["name"]
        assert "Delete=false" in options, item["metadata"]["name"]


def test_the_running_image_is_an_immutable_private_digest():
    container = named("Deployment", "gi")["spec"]["template"]["spec"]["containers"][0]
    assert DIGEST_IMAGE.match(container["image"]), container["image"]
    assert ":latest" not in container["image"]


def test_the_private_image_has_a_declared_pull_credential():
    """A private package needs a credential, and it is created from Vault inputs.

    Without this the pod can only ever report ImagePullBackOff, because the
    package denies anonymous pulls.
    """
    pod = named("Deployment", "gi")["spec"]["template"]["spec"]
    # No `optional` key: the API server discards it, so including it would make
    # Argo report permanent drift.
    assert pod["imagePullSecrets"] == [{"name": "gi-registry"}]

    bootstrap = (APP / "bootstrap-tasks.yml").read_text()
    assert "kind: Secret" in bootstrap
    assert "kubernetes.io/dockerconfigjson" in bootstrap
    assert "read:packages" in bootstrap
    # The credential is supplied from outside the repository.
    assert "gi_registry_token" in bootstrap
    assert "no_log: true" in bootstrap

    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "apps/gi"],
        cwd=ROOT,
        text=True,
    ).split()
    for name in tracked:
        assert not name.endswith(".vault.yml"), name


def test_only_one_writer_can_run_at_a_time():
    spec = named("Deployment", "gi")["spec"]
    assert spec["replicas"] == 1
    assert spec["strategy"]["type"] == "Recreate"


def test_workload_runs_unprivileged_with_an_immutable_root():
    pod = named("Deployment", "gi")["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert pod["automountServiceAccountToken"] is False
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]


def test_namespace_enforces_the_restricted_pod_security_standard():
    labels = named("Namespace", "gi")["metadata"]["labels"]
    assert labels["pod-security.kubernetes.io/enforce"] == "restricted"
    assert labels["pod-security.kubernetes.io/warn"] == "restricted"
    assert (
        labels["pod-security.kubernetes.io/enforce-version"]
        == labels["pod-security.kubernetes.io/warn-version"]
    )


def test_state_and_backups_use_separate_protected_claims():
    _, kinds, _ = rendered()
    claims = {item["metadata"]["name"]: item["spec"] for item in kinds["PersistentVolumeClaim"]}
    assert set(claims) == {"gi-data", "gi-backups"}
    for claim in claims.values():
        assert claim["storageClassName"] == "longhorn"
        assert claim["accessModes"] == ["ReadWriteOnce"]
    pod = named("Deployment", "gi")["spec"]["template"]["spec"]
    mounts = {mount["name"]: mount["mountPath"] for mount in pod["containers"][0]["volumeMounts"]}
    assert mounts["data"] == "/data"
    assert mounts["backups"] == "/backups"


def test_claims_are_outside_the_off_cluster_recovery_groups():
    """GI storage is home-cluster only, as PLAN.md requires.

    Longhorn only acts on a volume group named by a recurring job.  The two
    configured groups, `critical` and `durable-small`, both write to the
    off-cluster S3 target, so GI claims must not join either of them.
    """
    _, kinds, _ = rendered()
    for claim in kinds["PersistentVolumeClaim"]:
        labels = claim["metadata"].get("labels", {})
        groups = {
            key.split("/")[-1]
            for key in labels
            if key.startswith("recurring-job-group.longhorn.io/")
        }
        assert not groups & {"critical", "durable-small"}, claim["metadata"]["name"]

    jobs = list(
        yaml.safe_load_all((ROOT / "playbooks/operations/recovery/longhorn-jobs.yaml").read_text())
    )
    assert {group for job in jobs for group in job["spec"]["groups"]} == {
        "critical",
        "durable-small",
    }

    recovery = (ROOT / "playbooks/operations/recovery/configure-longhorn.yml").read_text()
    assert "gi-data" not in recovery
    assert "gi-backups" not in recovery


def test_whole_site_is_protected_by_forward_auth_before_the_backend():
    main = named("Ingress", "gi")
    annotations = main["metadata"]["annotations"]
    assert (
        "outpost.goauthentik.io/auth/nginx" in annotations["nginx.ingress.kubernetes.io/auth-url"]
    )
    assert annotations["nginx.ingress.kubernetes.io/auth-signin"].startswith(
        f"https://{HOSTNAME}/outpost.goauthentik.io/start"
    )
    assert annotations["nginx.ingress.kubernetes.io/auth-proxy-set-headers"] == (
        "gi/auth-proxy-set-headers-gi"
    )
    # Every request path is gated; there is no unprotected prefix.
    assert [path["path"] for path in main["spec"]["rules"][0]["http"]["paths"]] == ["/"]
    assert main["spec"]["rules"][0]["host"] == HOSTNAME
    assert main["spec"]["tls"][0]["secretName"] == "prod-cert-tls"


def test_the_outpost_route_exists_so_sign_in_can_complete():
    outpost = named("Ingress", "gi-authentik-outpost")
    assert outpost["spec"]["rules"][0]["http"]["paths"][0]["path"] == "/outpost.goauthentik.io"
    service = named("Service", "authentik-server-gi")
    assert service["spec"]["type"] == "ExternalName"
    assert service["spec"]["externalName"] == "authentik-server.authentik.svc.cluster.local"


def test_no_public_tunnel_or_extra_hostname_is_declared():
    _, kinds, resources = rendered()
    hosts = {rule["host"] for ingress in kinds["Ingress"] for rule in ingress["spec"]["rules"]}
    assert hosts == {HOSTNAME}
    assert "cloudflared" not in yaml.safe_dump(resources)


def test_only_the_dedicated_group_reaches_the_workspace():
    entries = blueprint("legacy-forward-auth.yaml")["entries"]
    binding = next(
        entry
        for entry in entries
        if entry["model"] == "authentik_policies.policybinding"
        and entry["identifiers"]["target"] == "gi-proxy-application"
    )
    assert find_target(binding["attrs"]["group"]) == "gi-users"

    provider = next(entry for entry in entries if entry.get("id") == "gi-proxy-provider")
    assert provider["attrs"]["external_host"] == f"https://{HOSTNAME}"
    assert provider["attrs"]["mode"] == "forward_single"

    outpost = next(entry for entry in entries if entry["model"] == "authentik_outposts.outpost")
    assert "gi-proxy-provider" in outpost["attrs"]["providers"]


def test_the_access_group_has_exactly_one_private_member_source():
    entries = blueprint("cluster-sso.yaml")["entries"]
    group = next(entry for entry in entries if entry.get("id") == "gi-users")
    assert group["identifiers"]["name"] == "gi-users"
    assert "attributes" not in group.get("attrs", {})

    holders = [
        entry["identifiers"]["username"]
        for entry in entries
        if entry["model"] == "authentik_core.user"
        and "gi-users" in entry.get("attrs", {}).get("groups", [])
    ]
    assert holders == ["boris"]


def test_the_member_entry_is_reconciled_on_every_apply():
    """Authentik skips an existing instance for `state: created`.

    With `created`, adding a group to this account would never reach an account
    that already exists, so the workspace group would stay empty.  `present`
    keeps the group list in step with the reviewed file.
    """
    entries = blueprint("cluster-sso.yaml")["entries"]
    user = next(entry for entry in entries if entry.get("id") == "boris-user")
    assert user["state"] == "present"
    assert "gi-users" in user["attrs"]["groups"]


def test_no_private_value_can_reach_the_public_package():
    """The public repository ships deployment only, never runtime content."""
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "apps/gi"],
        cwd=ROOT,
        text=True,
    ).split()
    allowed = {
        "apps/gi/Makefile",
        "apps/gi/README.md",
        "apps/gi/bootstrap-tasks.yml",
        "apps/gi/bootstrap.yml",
        "apps/gi/argocd/application.yaml",
        "apps/gi/argocd/kustomization.yaml",
        "apps/gi/argocd/project.yaml",
        "apps/gi/manifests/authentik-forward-auth.yaml",
        "apps/gi/manifests/certificate.yaml",
        "apps/gi/manifests/deployment.yaml",
        "apps/gi/manifests/ingress.yaml",
        "apps/gi/manifests/kustomization.yaml",
        "apps/gi/manifests/namespace.yaml",
        "apps/gi/manifests/pvc.yaml",
        "apps/gi/manifests/service.yaml",
        "apps/gi/tests/test_gi_boundary.py",
    }
    assert set(tracked) <= allowed, sorted(set(tracked) - allowed)
    scanned = sorted(allowed - {"apps/gi/tests/test_gi_boundary.py"})
    text = "\n".join((ROOT / name).read_text().lower() for name in scanned)
    for forbidden in ("datasetid", "monthly closing balance", "closingmortgagecents"):
        assert forbidden not in text
