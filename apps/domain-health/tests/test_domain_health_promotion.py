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


def legacy_package(tmp_path):
    app = tmp_path / "app"
    shutil.copytree(APP, app, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    # Rebuild the supported legacy fixture even after the live package uses an image.
    source = app / "app/domain-health-exporter.py"
    (app / "manifests/legacy-exporter.py").write_bytes(source.read_bytes())
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    pod = deployment["spec"]["template"]["spec"]
    pod["containers"][0].update(
        {
            "image": "python:3.12-slim",
            "command": ["python3", "/app/domain-health-exporter.py"],
            "volumeMounts": [{"name": "exporter-script", "mountPath": "/app", "readOnly": True}],
        }
    )
    pod["volumes"] = [
        {
            "name": "exporter-script",
            "configMap": {"name": "domain-health-exporter", "defaultMode": 0o555},
        }
    ]
    path.write_text(yaml.safe_dump(deployment, sort_keys=False))
    path = app / "kustomization.yaml"
    package = yaml.safe_load(path.read_text())
    package["configMapGenerator"] = [
        {
            "name": "domain-health-exporter",
            "files": ["domain-health-exporter.py=manifests/legacy-exporter.py"],
            "options": {"disableNameSuffixHash": True},
        }
    ]
    path.write_text(yaml.safe_dump(package, sort_keys=False))
    return app


def test_source_only_change_keeps_rendered_runtime_until_digest_promotion(tmp_path):
    app = legacy_package(tmp_path)
    before = render(app)
    source = app / "app/domain-health-exporter.py"
    source.write_text(source.read_text() + "\n# A source-only change must wait for promotion.\n")
    assert render(app) == before
    old_deployment = next(item for item in before if item["kind"] == "Deployment")
    promotion.promote(IMAGE, app)
    after = render(app)
    deployment = next(item for item in after if item["kind"] == "Deployment")
    old_pod = old_deployment["spec"]["template"]["spec"]
    pod = deployment["spec"]["template"]["spec"]
    exporter = pod["containers"][0]
    assert exporter["image"] == IMAGE
    assert exporter["env"] == old_pod["containers"][0]["env"]
    assert deployment["metadata"] == old_deployment["metadata"]
    assert deployment["spec"]["selector"] == old_deployment["spec"]["selector"]
    assert not any(item["kind"] == "ConfigMap" for item in after)
    assert pod["automountServiceAccountToken"] is False
    assert exporter["securityContext"]["readOnlyRootFilesystem"] is True
    assert "command" not in exporter and "volumeMounts" not in exporter
    next_image = IMAGE.replace("a" * 64, "b" * 64)
    promotion.promote(next_image, app)
    expected = after
    next(item for item in expected if item["kind"] == "Deployment")["spec"]["template"]["spec"][
        "containers"
    ][0]["image"] = next_image
    assert render(app) == expected


@pytest.mark.parametrize(
    "image,change",
    [
        ("ghcr.io/kpoxo6op/domain-health:latest", None),
        (IMAGE, lambda pod: pod["containers"][0].update(image="foreign/image:latest")),
        (IMAGE, lambda pod: pod["containers"][0].update(command=["other-runtime"])),
        (IMAGE, lambda pod: pod["containers"][0]["volumeMounts"][0].update(mountPath="/other")),
        (IMAGE, lambda pod: pod["volumes"][0]["configMap"].update(name="other-code")),
    ],
)
def test_promotion_rejects_unknown_runtime_before_changing_files(tmp_path, image, change):
    app = legacy_package(tmp_path)
    path = app / "manifests/deployment.yaml"
    if change:
        deployment = yaml.safe_load(path.read_text())
        change(deployment["spec"]["template"]["spec"])
        path.write_text(yaml.safe_dump(deployment))
    before = (path.read_bytes(), (app / "kustomization.yaml").read_bytes())
    with pytest.raises(ValueError):
        promotion.promote(image, app)
    assert (path.read_bytes(), (app / "kustomization.yaml").read_bytes()) == before


def test_image_update_rejects_an_unremoved_legacy_volume(tmp_path):
    app = legacy_package(tmp_path)
    promotion.promote(IMAGE, app)
    path = app / "manifests/deployment.yaml"
    deployment = yaml.safe_load(path.read_text())
    deployment["spec"]["template"]["spec"]["volumes"] = [
        {"name": "exporter-script", "configMap": {"name": "domain-health-exporter"}}
    ]
    path.write_text(yaml.safe_dump(deployment))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="legacy runtime settings"):
        promotion.promote(IMAGE.replace("a" * 64, "b" * 64), app)
    assert path.read_bytes() == before
