from scripts.validate_openapi_specs import validate
from scripts.synthetic_bank_config import APIS, ROOT

import yaml


def test_openapi_linter_passes():
    assert validate() == []


def test_openapi_specs_include_required_banklab_extensions():
    for api in APIS:
        spec = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / "openapi.yaml").read_text(encoding="utf-8"))
        assert spec["x-banklab-api-domain"] == api.key
        assert spec["x-banklab-lifecycle"] == "sandbox"
        assert spec["x-banklab-data-classification"] == "synthetic"
        assert spec["x-banklab-auth-profile"] == "none-temporary-goal003-sandbox"
        assert f"{api.prefix}/health" in spec["paths"]
