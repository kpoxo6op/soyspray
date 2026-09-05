import copy
import runpy
import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]

promote = runpy.run_path(ROOT / "apps/autism-traits/promote-image.py")["promote"]
IMAGE = "ghcr.io/kpoxo6op/autism-traits@sha256:" + "a" * 64


def read(path):
    return yaml.safe_load(path.read_text())


def test_promotion_changes_only_the_image_and_is_retryable(tmp_path):
    for name in ("deployment.yaml", "kustomization.yaml"):
        shutil.copy(ROOT / "apps/autism-traits/manifests" / name, tmp_path / name)
    before = read(tmp_path / "deployment.yaml")
    prior_kustomization = (tmp_path / "kustomization.yaml").read_bytes()
    expected = copy.deepcopy(before)
    pod = expected["spec"]["template"]["spec"]
    web = pod["containers"][0]
    web["image"] = IMAGE
    promote(IMAGE, tmp_path)
    assert read(tmp_path / "deployment.yaml") == expected
    assert (tmp_path / "kustomization.yaml").read_bytes() == prior_kustomization
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
