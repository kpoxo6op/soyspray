from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_policy_placeholder_files_exist():
    required = [
        "policies/conftest/README.md",
        "policies/conftest/placeholder.rego",
        "policies/examples/valid-api-metadata.yaml",
        "policies/examples/invalid-api-metadata.yaml",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert missing == []


def test_valid_api_metadata_has_required_fields():
    metadata = yaml.safe_load(
        (ROOT / "policies/examples/valid-api-metadata.yaml").read_text()
    )
    required = {
        "api_name",
        "owning_team",
        "exposure",
        "lifecycle_state",
        "data_classification",
        "support_contact",
        "slo_target",
        "auth_profile",
        "rate_limit_profile",
    }
    assert required.issubset(metadata)
    assert all(metadata[field] for field in required)


def test_invalid_api_metadata_is_intentionally_incomplete():
    metadata = yaml.safe_load(
        (ROOT / "policies/examples/invalid-api-metadata.yaml").read_text()
    )
    empty_fields = [field for field, value in metadata.items() if not value]
    assert empty_fields

