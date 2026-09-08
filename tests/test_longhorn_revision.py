from conftest import load_yaml


def test_longhorn_follows_main_through_the_native_catalog():
    application = load_yaml("argocd/catalog/longhorn.yaml")
    assert application["spec"]["source"]["targetRevision"] == "main"
    assert application["metadata"].get("finalizers", []) == []
