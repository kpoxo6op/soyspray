from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_versions_are_pinned():
    versions = load("platform/kong/versions.yaml")
    assert versions["kong_gateway"]["image_repository"] == "kong"
    assert versions["kong_gateway"]["image_tag"] == "3.9.3"
    assert versions["kong_ingress_controller"]["image_tag"] == "3.5.10"
    assert versions["helm"]["chart_name"] == "kong/ingress"
    assert versions["helm"]["chart_version"] == "0.24.0"
    assert versions["gateway_api"]["version"] == "v1.3.0"


def test_helm_values_match_version_lock():
    versions = load("platform/kong/versions.yaml")
    values = load("platform/kong/helm/values-kong-oss-baseline.yaml")
    assert values["gateway"]["image"]["repository"] == versions["kong_gateway"]["image_repository"]
    assert values["gateway"]["image"]["tag"] == versions["kong_gateway"]["image_tag"]
    assert (
        values["controller"]["ingressController"]["image"]["tag"]
        == versions["kong_ingress_controller"]["image_tag"]
    )


def test_no_latest_tags_in_kong_yaml():
    offenders = []
    for path in (ROOT / "platform/kong").rglob("*.yaml"):
        if "gateway-api/crds" in path.as_posix():
            continue
        if ":latest" in path.read_text() or " latest" in path.read_text().lower():
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
