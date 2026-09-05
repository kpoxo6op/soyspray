import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "playbooks/argocd/applications/database/obsidian-livesync"
APP = ROOT / "apps/obsidian-livesync"


def test_original_couchdb_writer_and_claim_keep_their_identities():
    result = subprocess.run(
        ["kubectl", "kustomize", str(PACKAGE)], check=True, capture_output=True, text=True
    )
    objects = {
        item["kind"] + "/" + item["metadata"]["name"]: item
        for item in yaml.safe_load_all(result.stdout)
    }
    deployment = objects["Deployment/obsidian-livesync-couchdb-hostpath-rescue"]
    spec = deployment["spec"]
    assert spec["replicas"] == 1
    assert spec["strategy"] == {"type": "Recreate"}
    pod = spec["template"]["spec"]
    data = next(volume for volume in pod["volumes"] if volume["name"] == "data")
    assert data["persistentVolumeClaim"]["claimName"] == "obsidian-livesync-couchdb-rescue-longhorn"
    server = pod["containers"][0]
    assert server["image"] == "couchdb:3.4.2"
    assert (
        next(mount for mount in server["volumeMounts"] if mount["name"] == "data")["mountPath"]
        == "/opt/couchdb/data"
    )
    assert {
        entry["valueFrom"]["secretKeyRef"]["name"]
        for entry in server["env"]
        if "valueFrom" in entry
    } == {"obsidian-livesync-couchdb"}
    for key in [
        "Namespace/obsidian",
        "PersistentVolumeClaim/obsidian-livesync-couchdb-rescue-longhorn",
    ]:
        assert set(
            objects[key]["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
        ) == {"Prune=false", "Delete=false"}
    claim = objects["PersistentVolumeClaim/obsidian-livesync-couchdb-rescue-longhorn"]
    assert claim["spec"]["storageClassName"] == "longhorn"
    assert claim["spec"]["resources"]["requests"]["storage"] == "10Gi"
    assert claim["spec"]["accessModes"] == ["ReadWriteOnce"]
    ingress = objects["Ingress/obsidian-livesync-ingress"]
    assert ingress["spec"]["rules"][0]["host"] == "obsidian.soyspray.vip"


def test_native_ownership_has_bounded_permissions_and_storage_metadata():
    app = yaml.safe_load((APP / "argocd/application.yaml").read_text())
    project = yaml.safe_load((APP / "argocd/project.yaml").read_text())
    assert app["metadata"]["name"] == "obsidian-livesync"
    assert not app["metadata"].get("finalizers")
    assert (
        app["metadata"]["annotations"]["soyspray.vip/data-claims"]
        == "obsidian/obsidian-livesync-couchdb-rescue-longhorn"
    )
    assert app["spec"]["source"]["path"] == str(PACKAGE.relative_to(ROOT))
    assert app["spec"]["source"]["targetRevision"] == "HEAD"
    assert app["spec"]["project"] == project["metadata"]["name"] == "obsidian-livesync"
    for obj in [app, project]:
        assert set(
            obj["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
        ) == {"Prune=false", "Delete=false"}
    assert project["spec"]["sourceRepos"] == ["https://github.com/kpoxo6op/soyspray.git"]
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "obsidian"}
    ]
    assert project["spec"]["clusterResourceWhitelist"] == [{"group": "", "kind": "Namespace"}]
    assert {
        (item["group"], item["kind"]) for item in project["spec"]["namespaceResourceWhitelist"]
    } == {
        ("", "ConfigMap"),
        ("", "Service"),
        ("", "PersistentVolumeClaim"),
        ("apps", "Deployment"),
        ("networking.k8s.io", "Ingress"),
        ("networking.k8s.io", "NetworkPolicy"),
    }
