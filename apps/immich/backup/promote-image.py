"""Record a tested script image in native Kustomize image configuration."""

import argparse
import re
from pathlib import Path

import yaml


def promote(image, package):
    match = re.fullmatch(r"ghcr\.io/kpoxo6op/immich-backup-scripts@(sha256:[0-9a-f]{64})", image)
    if not match:
        raise ValueError("A tested Immich backup script image digest is required.")
    path = package / "kustomization.yaml"
    document = yaml.safe_load(path.read_text())
    if document.get("kind") != "Kustomization":
        raise ValueError("Expected native Kustomize configuration.")
    images = document.setdefault("images", [])
    prior = [entry for entry in images if entry["name"] == "immich-backup-scripts"]
    if len(prior) > 1:
        raise ValueError("The script image has duplicate declarations.")
    updated = {
        "name": "immich-backup-scripts",
        "newName": "ghcr.io/kpoxo6op/immich-backup-scripts",
        "digest": match.group(1),
    }
    if prior:
        images[images.index(prior[0])] = updated
    else:
        images.append(updated)
    path.write_text(yaml.safe_dump(document, sort_keys=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    args = parser.parse_args()
    promote(args.image, Path(__file__).resolve().parent)
