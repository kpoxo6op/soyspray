from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def yaml_docs(path: Path):
    return [doc for doc in yaml.safe_load_all(path.read_text()) if isinstance(doc, dict)]


def test_network_policy_baseline_files_contain_network_policies():
    required = [
        "platform-default-deny.yaml",
        "tenants-default-deny.yaml",
        "allow-dns.yaml",
        "allow-gitops-to-managed-namespaces.yaml",
        "allow-observability-scrape-placeholder.yaml",
        "allow-ingress-controller-placeholder.yaml",
    ]
    base = ROOT / "platform/networking/network-policies"
    for filename in required:
        kinds = {doc.get("kind") for doc in yaml_docs(base / filename)}
        assert "NetworkPolicy" in kinds


def test_namespace_policy_labels_are_enforced_by_fixtures():
    for path in (ROOT / "platform/namespaces").glob("*.yaml"):
        if path.name == "kustomization.yaml":
            continue
        labels = yaml.safe_load(path.read_text())["metadata"]["labels"]
        assert labels["banklab.konghq.com/platform-layer"] == "prereq"
        assert labels["banklab.konghq.com/data-classification"] == "synthetic"
        assert labels["banklab.konghq.com/owner"]


def test_plaintext_secret_manifests_are_limited_to_non_deployable_examples():
    secret_docs = []
    for path in (ROOT / "platform").rglob("*.yaml"):
        for doc in yaml_docs(path):
            if doc.get("kind") == "Secret":
                secret_docs.append((path, doc))
    assert len(secret_docs) == 1
    path, doc = secret_docs[0]
    annotations = doc.get("metadata", {}).get("annotations", {})
    assert path.name == "encrypted-secret.example.yaml"
    assert annotations.get("banklab.konghq.com/non-deployable") == "true"

