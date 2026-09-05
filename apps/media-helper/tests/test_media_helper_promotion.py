import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("media_helper_promotion", APP / "promote-image.py")
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)
IMAGE = "ghcr.io/kpoxo6op/media-helper@sha256:" + "a" * 64


def package(tmp_path):
    app = tmp_path / "app"
    shutil.copytree(APP, app, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    return app


def render(app):
    return list(
        yaml.safe_load_all(subprocess.check_output(["kubectl", "kustomize", str(app)], text=True))
    )


def test_source_and_catalog_wait_for_a_digest_promotion(tmp_path):
    app = package(tmp_path)
    before = render(app)
    source = app / "app/app.py"
    source.write_text(source.read_text() + "\n# Source-only fixture.\n")
    catalog = app / "app/channels.json"
    value = json.loads(catalog.read_text())
    value["channels"][0]["name"] = "Changed source-only fixture"
    catalog.write_text(json.dumps(value))
    assert render(app) == before
    promotion.promote(IMAGE, app)
    expected = before
    pod = next(item for item in expected if item["kind"] == "Deployment")["spec"]["template"][
        "spec"
    ]
    container = pod["containers"][0]
    container["image"] = IMAGE
    assert render(app) == expected
    promotion.promote(IMAGE, app)
    assert render(app) == expected
    next_image = IMAGE[:-64] + "b" * 64
    promotion.promote(next_image, app)
    container["image"] = next_image
    assert render(app) == expected


@pytest.mark.parametrize(
    "change",
    [
        "tag",
        "foreign-image",
        "previous-image",
        "command",
        "args",
        "mount",
        "volume",
        "generator",
        "namespace",
        "deployment",
        "readiness",
    ],
)
def test_unknown_transitions_stop_before_either_document_changes(tmp_path, change):
    app = package(tmp_path)
    path, package_path = app / "manifests/deployment.yaml", app / "kustomization.yaml"
    deployment, root = yaml.safe_load(path.read_text()), yaml.safe_load(package_path.read_text())
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]
    image = IMAGE
    if change == "tag":
        image = "ghcr.io/kpoxo6op/media-helper:latest"
    elif change == "foreign-image":
        image = IMAGE.replace("kpoxo6op", "foreign")
    elif change == "previous-image":
        container["image"] = "foreign/image:latest"
    elif change in ("command", "args"):
        container[change] = ["unexpected"]
    elif change == "mount":
        container["volumeMounts"].append({"name": "code", "mountPath": "/other"})
    elif change == "volume":
        pod["volumes"].append({"name": "code", "configMap": {"name": "other"}})
    elif change == "generator":
        root["configMapGenerator"] = [{"name": "media-helper-code", "files": ["app.py=app/app.py"]}]
    elif change == "namespace":
        root["namespace"] = "other"
    elif change == "readiness":
        container["readinessProbe"]["httpGet"]["path"] = "/other"
    elif change == "deployment":
        deployment["metadata"]["name"] = "other"
    path.write_text(yaml.safe_dump(deployment))
    package_path.write_text(yaml.safe_dump(root))
    before = path.read_bytes(), package_path.read_bytes()
    with pytest.raises(ValueError):
        promotion.promote(image, app)
    assert (path.read_bytes(), package_path.read_bytes()) == before
