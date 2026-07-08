import yaml

from scripts.synthetic_bank_config import APIS, ROOT


def test_each_api_allows_only_kong_to_mock_backend_port():
    for api in APIS:
        policy = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / "networkpolicy-allow-kong.yaml").read_text(encoding="utf-8"))
        assert policy["kind"] == "NetworkPolicy"
        assert policy["metadata"]["namespace"] == api.namespace
        ingress = policy["spec"]["ingress"]
        assert ingress[0]["ports"] == [{"protocol": "TCP", "port": 8080}]
        source = ingress[0]["from"][0]
        assert source["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"] == "platform-kong"
        assert source["podSelector"]["matchLabels"]["banklab.konghq.com/component"] == "gateway"


def test_kong_gateway_egress_is_limited_to_synthetic_api_upstreams():
    policy = yaml.safe_load((ROOT / "platform/kong/synthetic-apis/kong-allow-synthetic-api-upstreams.yaml").read_text(encoding="utf-8"))
    assert policy["kind"] == "NetworkPolicy"
    assert policy["metadata"]["namespace"] == "platform-kong"
    assert policy["spec"]["podSelector"]["matchLabels"]["banklab.konghq.com/component"] == "gateway"
    assert policy["spec"]["policyTypes"] == ["Egress"]

    egress = policy["spec"]["egress"]
    assert egress[0]["ports"] == [{"protocol": "TCP", "port": 8080}]
    peers = egress[0]["to"]
    assert {peer["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"] for peer in peers} == {api.namespace for api in APIS}
    for peer in peers:
        assert peer["podSelector"]["matchLabels"]["banklab.konghq.com/platform-layer"] == "synthetic-api"
        assert peer["podSelector"]["matchLabels"]["banklab.konghq.com/goal"] == "goal-003"
