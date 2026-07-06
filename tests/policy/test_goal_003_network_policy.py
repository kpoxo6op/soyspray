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
