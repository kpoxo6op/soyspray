import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("domain_health_promotion", APP / "promote-image.py")
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)
IMAGE = "ghcr.io/kpoxo6op/domain-health@sha256:" + "a" * 64


def render(app):
    return list(
        yaml.safe_load_all(subprocess.check_output(["kubectl", "kustomize", str(app)], text=True))
    )


def package(tmp_path):
    app = tmp_path / "app"
    shutil.copytree(APP, app, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    return app


def test_source_only_changes_wait_for_a_digest_and_promotion_changes_only_the_image(tmp_path):
    app = package(tmp_path)
    before = render(app)
    source = app / "app/domain-health-exporter.py"
    source.write_text(source.read_text() + "\n# Source changes wait for promotion.\n")
    assert render(app) == before
    promotion.promote(IMAGE, app)
    deployment = next(item for item in before if item["kind"] == "Deployment")
    deployment["spec"]["template"]["spec"]["containers"][0]["image"] = IMAGE
    assert render(app) == before
    promotion.promote(IMAGE, app)
    assert render(app) == before


@pytest.mark.parametrize(
    "image,change",
    [
        ("ghcr.io/kpoxo6op/domain-health:latest", {}),
        ("ghcr.io/foreign/domain-health@sha256:" + "a" * 64, {}),
        (IMAGE, {"image": "foreign/image:latest"}),
        (IMAGE, {"command": ["other-runtime"]}),
        (IMAGE, {"args": ["other-runtime"]}),
        (IMAGE, {"volumeMounts": [{"name": "script", "mountPath": "/app"}]}),
    ],
)
def test_promotion_rejects_unknown_runtime_before_changing_files(tmp_path, image, change):
    app = package(tmp_path)
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    deployment["spec"]["template"]["spec"]["containers"][0].update(change)
    path.write_text(yaml.safe_dump(deployment))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        promotion.promote(image, app)
    assert path.read_bytes() == before
