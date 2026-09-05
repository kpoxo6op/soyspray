import importlib.util

import pytest
import yaml
from conftest import ROOT

spec = importlib.util.spec_from_file_location(
    "immich_promotion", ROOT / "apps/immich/backup/promote-image.py"
)
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)


@pytest.mark.parametrize("prior", [False, True])
def test_promotion_preserves_resources_and_other_image_pins(tmp_path, prior):
    document = {
        "apiVersion": "kustomize.config.k8s.io/v1beta1",
        "kind": "Kustomization",
        "resources": ["cronjob.yaml"],
        "namespace": "immich",
        "images": [{"name": "postgres", "digest": "sha256:" + "b" * 64}],
    }
    if prior:
        document["images"].append(
            {"name": "immich-backup-scripts", "newTag": "old", "newName": "old-repository"}
        )
    path = tmp_path / "kustomization.yaml"
    path.write_text(yaml.safe_dump(document))
    image = "ghcr.io/kpoxo6op/immich-backup-scripts@sha256:" + "a" * 64
    promotion.promote(image, tmp_path)
    updated = yaml.safe_load(path.read_text())
    assert updated == {
        **document,
        "images": [
            document["images"][0],
            {
                "name": "immich-backup-scripts",
                "newName": "ghcr.io/kpoxo6op/immich-backup-scripts",
                "digest": "sha256:" + "a" * 64,
            },
        ],
    }
    first = path.read_bytes()
    promotion.promote(image, tmp_path)
    assert path.read_bytes() == first


@pytest.mark.parametrize(
    "image",
    [
        "ghcr.io/kpoxo6op/immich-backup-scripts:latest",
        "ghcr.io/other/immich-backup-scripts@sha256:" + "a" * 64,
        "ghcr.io/kpoxo6op/immich-backup-scripts@sha256:short",
    ],
)
def test_promotion_rejects_unpinned_or_unexpected_images_without_writing(tmp_path, image):
    path = tmp_path / "kustomization.yaml"
    path.write_text("kind: Kustomization\nresources: []\n")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        promotion.promote(image, tmp_path)
    assert path.read_bytes() == before
