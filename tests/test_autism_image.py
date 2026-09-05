import copy
import runpy
import shutil

import pytest
import yaml
from conftest import ROOT

promote = runpy.run_path(ROOT / "apps/autism-traits/promote-image.py")["promote"]
IMAGE = "ghcr.io/kpoxo6op/autism-traits@sha256:" + "a" * 64


def read(path):
    return yaml.safe_load(path.read_text())


def test_promotion_adopts_embedded_files_and_preserves_access(tmp_path):
    for name in ("deployment.yaml", "kustomization.yaml"):
        shutil.copy(ROOT / "kubernetes/autism-traits" / name, tmp_path / name)
    before = read(tmp_path / "deployment.yaml")
    prior_resources = read(tmp_path / "kustomization.yaml")["resources"]
    expected = copy.deepcopy(before)
    pod = expected["spec"]["template"]["spec"]
    web = pod["containers"][0]
    web["image"] = IMAGE
    web["volumeMounts"] = [m for m in web["volumeMounts"] if m["name"] in {"tls", "tmp"}]
    pod["volumes"] = [v for v in pod["volumes"] if v["name"] in {"tls", "tmp"}]
    promote(IMAGE, tmp_path)
    assert read(tmp_path / "deployment.yaml") == expected
    assert read(tmp_path / "kustomization.yaml")["resources"] == prior_resources
    first = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    promote(IMAGE, tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == first
    next_image = IMAGE[:-1] + "b"
    promote(next_image, tmp_path)
    expected["spec"]["template"]["spec"]["containers"][0]["image"] = next_image
    assert read(tmp_path / "deployment.yaml") == expected


@pytest.mark.parametrize("image", ["latest", "ghcr.io/other/app@sha256:" + "a" * 64])
def test_invalid_image_cannot_write_a_promotion(tmp_path, image):
    with pytest.raises(ValueError, match="digest"):
        promote(image, tmp_path)
    assert not list(tmp_path.iterdir())
