"""Promote only a tested Memes image; never enable workloads or register Argo."""

import re
import sys
from pathlib import Path

import yaml


def promote(image, path):
    match = re.fullmatch(r"(ghcr.io/kpoxo6op/memes(?:-import)?)@(sha256:[0-9a-f]{64})", image)
    if not match:
        raise ValueError("Expected a Memes image digest")
    package = yaml.safe_load(path.read_text())
    entries = [entry for entry in package["images"] if entry["name"] == match[1]]
    if len(entries) != 1:
        raise ValueError("Expected exactly one matching image entry")
    entries[0].pop("newTag", None)
    entries[0]["digest"] = match[2]
    path.write_text(yaml.safe_dump(package, sort_keys=False))


if __name__ == "__main__":
    promote(sys.argv[1], Path(__file__).with_name("manifests") / "kustomization.yaml")
