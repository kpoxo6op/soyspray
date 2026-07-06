from pathlib import Path

import yaml

from scripts.synthetic_bank_config import FORBIDDEN_KINDS, ROOT


def yaml_docs(path: Path):
    return [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(doc, dict)]


def test_no_forbidden_kong_resources_in_synthetic_api_layer():
    offenders = []
    for path in (ROOT / "apis/synthetic-bank").rglob("*.yaml"):
        if path.name in {"openapi.yaml", "ownership.yaml", "kustomization.yaml"}:
            continue
        for doc in yaml_docs(path):
            if doc.get("kind") in FORBIDDEN_KINDS:
                offenders.append((str(path.relative_to(ROOT)), doc["kind"]))
    assert offenders == []
