from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_NAMESPACES = {
    "platform-system",
    "platform-gitops",
    "platform-security",
    "platform-networking",
    "platform-observability",
    "platform-identity",
    "tenant-accounts",
    "tenant-payments",
    "tenant-cards",
    "tenant-customer-profile",
    "tenant-fraud",
    "tenant-open-banking",
    "synthetic-clients",
}

REQUIRED_LABELS = {
    "banklab.konghq.com/managed-by": "gitops",
    "banklab.konghq.com/platform-layer": "prereq",
    "banklab.konghq.com/environment": "lab",
    "banklab.konghq.com/data-classification": "synthetic",
}


def load_namespace(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_required_namespaces_are_declared():
    declared = {
        load_namespace(path)["metadata"]["name"]
        for path in (ROOT / "platform/namespaces").glob("*.yaml")
        if path.name != "kustomization.yaml"
    }
    assert declared == REQUIRED_NAMESPACES


def test_namespace_labels_are_present():
    for namespace in REQUIRED_NAMESPACES:
        data = load_namespace(ROOT / "platform/namespaces" / f"{namespace}.yaml")
        labels = data["metadata"]["labels"]
        for key, expected in REQUIRED_LABELS.items():
            assert labels[key] == expected
        assert labels["banklab.konghq.com/owner"]

