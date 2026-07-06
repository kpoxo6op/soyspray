from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "platform/kong/versions.yaml",
    "platform/kong/namespace.yaml",
    "platform/kong/helm/values-kong-oss-baseline.yaml",
    "platform/kong/gateway-api/gatewayclass-kong.yaml",
    "platform/kong/gateway-api/gateway-external.yaml",
    "platform/kong/gateway-api/gateway-internal.yaml",
    "platform/kong/smoke/deployment.yaml",
    "platform/kong/smoke/service.yaml",
    "platform/kong/smoke/httproute-external.yaml",
    "platform/kong/smoke/httproute-internal.yaml",
    "platform/kong/network-policies/kong-default-deny.yaml",
    "platform/kong/argocd/kong-baseline-app.yaml",
    "platform/gitops/app-of-apps/kong-baseline-app.yaml",
    "reports/goal-002-summary.md",
]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_goal_002_required_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_kong_namespaces_are_platform_owned():
    kong = load("platform/kong/namespace.yaml")
    smoke = load("platform/kong/smoke/namespace.yaml")
    assert kong["metadata"]["name"] == "platform-kong"
    assert smoke["metadata"]["name"] == "platform-kong-smoke"
    assert kong["metadata"]["labels"]["banklab.konghq.com/platform-layer"] == "gateway"
    assert smoke["metadata"]["labels"]["banklab.konghq.com/platform-layer"] == "gateway"


def test_gateway_api_baseline_exists():
    gateway_class = load("platform/kong/gateway-api/gatewayclass-kong.yaml")
    external = load("platform/kong/gateway-api/gateway-external.yaml")
    internal = load("platform/kong/gateway-api/gateway-internal.yaml")
    assert gateway_class["kind"] == "GatewayClass"
    assert gateway_class["spec"]["controllerName"] == "konghq.com/kic-gateway-controller"
    assert external["kind"] == "Gateway"
    assert internal["kind"] == "Gateway"

