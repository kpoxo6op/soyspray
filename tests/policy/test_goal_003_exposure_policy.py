import yaml

from scripts.synthetic_bank_config import APIS, ROOT


def test_internal_apis_do_not_attach_to_external_gateway():
    for api in APIS:
        route_file = "httproute-external.yaml" if api.exposure == "external" else "httproute-internal.yaml"
        route = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / route_file).read_text(encoding="utf-8"))
        assert route["spec"]["hostnames"] == [api.host]
        assert route["spec"]["parentRefs"][0]["name"] == api.gateway
        if api.exposure == "internal":
            assert api.gateway == "kong-internal"
            assert api.host == "api.internal.banklab.test"
            assert not (ROOT / "apis/synthetic-bank" / api.key / "httproute-external.yaml").exists()
        else:
            assert api.key == "open-banking"
            assert api.gateway == "kong-external"
            assert api.host == "api.external.banklab.test"
