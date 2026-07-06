from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_admin_api_is_cluster_private_in_values():
    values = load("platform/kong/helm/values-kong-oss-baseline.yaml")
    admin = values["gateway"]["admin"]
    assert admin["enabled"] is True
    assert admin["type"] == "ClusterIP"
    assert admin["ingress"]["enabled"] is False
    assert admin["http"]["enabled"] is False


def test_gateway_routes_do_not_reference_admin_api():
    route_files = list((ROOT / "platform/kong").rglob("*route*.yaml"))
    offenders = [
        str(path.relative_to(ROOT))
        for path in route_files
        if "admin" in path.read_text().lower()
    ]
    assert offenders == []


def test_proxy_service_is_load_balancer():
    values = load("platform/kong/helm/values-kong-oss-baseline.yaml")
    assert values["gateway"]["proxy"]["type"] == "LoadBalancer"


def test_admin_api_network_path_is_controller_only():
    ingress = load("platform/kong/network-policies/kong-allow-admin-from-controller.yaml")
    rule = ingress["spec"]["ingress"][0]
    assert ingress["spec"]["podSelector"]["matchLabels"] == {
        "banklab.konghq.com/component": "gateway"
    }
    assert rule["from"][0]["podSelector"]["matchLabels"] == {
        "banklab.konghq.com/component": "kic"
    }
    assert rule["ports"] == [{"protocol": "TCP", "port": 8444}]

    egress = load("platform/kong/network-policies/kong-allow-controller-admin.yaml")
    rule = egress["spec"]["egress"][0]
    assert egress["spec"]["podSelector"]["matchLabels"] == {
        "banklab.konghq.com/component": "kic"
    }
    assert rule["to"][0]["podSelector"]["matchLabels"] == {
        "banklab.konghq.com/component": "gateway"
    }
    assert rule["ports"] == [{"protocol": "TCP", "port": 8444}]
