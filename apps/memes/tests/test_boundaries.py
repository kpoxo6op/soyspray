"""Security and release safety absent from other applications' tests."""

import importlib.util
import subprocess
import urllib.error
from pathlib import Path

import pytest
import yaml
from e2e import Client
from fixture import synthetic
from memes.catalog import Catalog
from memes.server import server

ROOT = Path(__file__).resolve().parents[3]
APP = Path(__file__).resolve().parents[1]


def test_authentication_csrf_and_tester_isolation(tmp_path):
    """Possessing a different invite cannot read another tester's images or submit a cross-origin click."""
    import threading

    synthetic(tmp_path)
    http = server(tmp_path, ("127.0.0.1", 0), origin="http://allowed", secure=False)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    client = Client(f"http://127.0.0.1:{http.server_address[1]}")
    try:
        for path in ("/api/feed", "/api/results", "/results", "/images/0"):
            with pytest.raises(urllib.error.HTTPError) as error:
                client.request(path)
            assert error.value.code == 401
        token = http.store.invite("one")
        first = http.store.authenticate(http.store.exchange(token))
        head = http.store.feed(first)["items"][0]
        client.request("/t/" + http.store.invite("two"))
        with pytest.raises(urllib.error.HTTPError) as error:
            client.request(head["image"])
        assert error.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as error:
            client.request(
                "/api/action",
                {
                    "impression_id": head["impression_id"],
                    "action": "like",
                    "hidden_ms": 0,
                    "client_seq": 1,
                },
            )
        assert error.value.code == 403
        assert http.store.results(first)["warmup"]["likes"] == 0
    finally:
        http.shutdown()
        http.server_close()
        thread.join()


def test_corrupt_catalog_refuses_startup(tmp_path):
    """A damaged vectors/catalog copy must fail closed rather than misalign item scores."""
    synthetic(tmp_path)
    path = tmp_path / "catalog/vectors.npy"
    path.write_bytes(path.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        Catalog(tmp_path / "catalog")


def test_deployment_archive_and_private_boundary():
    """Rendering must preserve read-only source access, private ingress and one-writer rollout."""
    resources = list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(APP / "manifests")], text=True)
        )
    )
    by_name = {(r["kind"], r["metadata"]["name"]): r for r in resources}
    web = by_name[("Deployment", "memes")]
    assert web["spec"]["replicas"] <= 1 and web["spec"]["strategy"]["type"] == "Recreate"
    # Kubernetes creates MEMES_PORT=tcp://... for the namesake Service; local/image tests lack it.
    assert web["spec"]["template"]["spec"]["enableServiceLinks"] is False
    jobs = [r for r in resources if r["kind"] == "Job"]
    for job in jobs:
        for container in job["spec"]["template"]["spec"]["containers"]:
            if not job["spec"]["suspend"]:
                assert "@sha256:" in container["image"]
            requests, limits = container["resources"]["requests"], container["resources"]["limits"]

            def cpu(value):
                return float(value[:-1]) / 1000 if value.endswith("m") else float(value)

            assert cpu(requests["cpu"]) <= cpu(limits["cpu"])

    def wave(r):
        return int(r["metadata"].get("annotations", {}).get("argocd.argoproj.io/sync-wave", "0"))

    prepare = by_name[("Job", "memes-prepare-v1")]
    import_job = by_name[("Job", "memes-import-v1")]
    assert wave(prepare) < wave(import_job) <= wave(web)
    assert all(
        wave(r) < wave(prepare)
        for r in resources
        if r["kind"] in ("PersistentVolume", "PersistentVolumeClaim", "Namespace", "NetworkPolicy")
    )
    importer = by_name[("Job", "memes-import-v1")]["spec"]["template"]["spec"]
    assert "fsGroup" not in importer["securityContext"]
    assert importer["nodeSelector"] == {"kubernetes.io/hostname": "node-0"}
    assert importer["containers"][0]["resources"]["limits"]["cpu"] == "4"
    assert next(v for v in importer["volumes"] if v["name"] == "archive")["persistentVolumeClaim"][
        "readOnly"
    ]
    assert next(m for m in importer["containers"][0]["volumeMounts"] if m["name"] == "archive")[
        "readOnly"
    ]
    for resource in resources:
        if resource["kind"] in ("PersistentVolume", "PersistentVolumeClaim", "Namespace"):
            assert set(
                resource["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
            ) >= {"Prune=false", "Delete=false"}
    pv = by_name[("PersistentVolume", "memes-vk-archive")]
    assert pv["spec"]["persistentVolumeReclaimPolicy"] == "Retain"
    ingress = by_name[("Ingress", "memes")]
    annotations = ingress["metadata"]["annotations"]
    assert annotations["nginx.ingress.kubernetes.io/enable-access-log"] == "false"
    assert not any(k.startswith("external-dns") for k in annotations)
    assert by_name[("NetworkPolicy", "memes-isolation")]["spec"]["egress"] == []
    root_resources = list(
        yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(ROOT / "argocd")], text=True)
        )
    )
    application = next(
        r for r in root_resources if r["kind"] == "Application" and r["metadata"]["name"] == "memes"
    )
    assert application["spec"]["source"]["targetRevision"] == "main"
    assert application["spec"]["syncPolicy"]["automated"]["prune"] is False


def test_promotion_changes_only_matching_digest(tmp_path):
    """A promotion must preserve the other digest and completed Jobs' immutable templates."""
    import shutil

    spec = importlib.util.spec_from_file_location("memes_promotion", APP / "promote-image.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    package = tmp_path / "manifests"
    shutil.copytree(APP / "manifests", package)
    path = package / "kustomization.yaml"

    def jobs():
        resources = yaml.safe_load_all(
            subprocess.check_output(["kubectl", "kustomize", str(package)], text=True)
        )
        return {
            r["metadata"]["name"]: r["spec"]["template"] for r in resources if r["kind"] == "Job"
        }

    original_jobs = jobs()
    original = yaml.safe_load(path.read_text())
    for image, char in [("memes", "a"), ("memes-import", "b")]:
        module.promote(f"ghcr.io/kpoxo6op/{image}@sha256:" + char * 64, path)
    promoted = yaml.safe_load(path.read_text())
    assert promoted["resources"] == original["resources"]
    images = {i["name"]: i for i in promoted["images"]}
    assert images["ghcr.io/kpoxo6op/memes"]["digest"] == "sha256:" + "a" * 64
    assert images["ghcr.io/kpoxo6op/memes-import"]["digest"] == "sha256:" + "b" * 64
    assert [i for i in promoted["images"] if i["name"].endswith("-v1")] == [
        i for i in original["images"] if i["name"].endswith("-v1")
    ]
    assert jobs() == original_jobs
    with pytest.raises(ValueError):
        module.promote("ghcr.io/kpoxo6op/memes:latest", path)


def test_importer_promotion_action_entrypoint(tmp_path):
    """Importer action routing must reach the digest editor; helper tests do not exercise its script path."""
    import shutil

    root = tmp_path / "memes"
    (root / "import").mkdir(parents=True)
    (root / "manifests").mkdir()
    for relative in ("promote-image.py", "import/promote-image.py", "manifests/kustomization.yaml"):
        shutil.copyfile(APP / relative, root / relative)
    initial = yaml.safe_load((root / "manifests/kustomization.yaml").read_text())["images"][0]
    digest = "sha256:" + "b" * 64
    subprocess.run(
        [
            __import__("sys").executable,
            str(root / "import/promote-image.py"),
            "ghcr.io/kpoxo6op/memes-import@" + digest,
        ],
        check=True,
    )
    package = yaml.safe_load((root / "manifests/kustomization.yaml").read_text())
    images = {i["name"]: i for i in package["images"]}
    assert images["ghcr.io/kpoxo6op/memes-import"]["digest"] == digest
    assert images["ghcr.io/kpoxo6op/memes"] == initial
