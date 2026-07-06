from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_enterprise_features_are_disabled():
    values = load("platform/kong/helm/values-kong-oss-baseline.yaml")
    gateway = values["gateway"]
    assert gateway["enterprise"]["enabled"] is False
    assert gateway["enterprise"]["portal"]["enabled"] is False
    assert gateway["enterprise"]["rbac"]["enabled"] is False
    assert gateway["manager"]["enabled"] is False
    assert gateway["portal"]["enabled"] is False
    assert gateway["portalapi"]["enabled"] is False


def test_dbless_mode_without_postgres():
    values = load("platform/kong/helm/values-kong-oss-baseline.yaml")
    assert values["gateway"]["env"]["database"] == "off"
    assert values["gateway"]["postgresql"]["enabled"] is False


def test_no_forbidden_enterprise_text_in_kong_manifests():
    forbidden = ["kong/kong-gateway", "openid-connect", "request-validator", "mtls-auth"]
    offenders = []
    for path in (ROOT / "platform/kong").rglob("*"):
        if path.is_file() and path.suffix in {".yaml", ".yml"}:
            content = path.read_text()
            for term in forbidden:
                if term in content:
                    offenders.append((str(path.relative_to(ROOT)), term))
    assert offenders == []

