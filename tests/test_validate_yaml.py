import pytest
import yaml

from scripts import validate_yaml


def test_a_key_written_twice_is_rejected():
    text = "operator:\n  a: 1\nother: 2\noperator:\n  b: 2\n"
    with pytest.raises(yaml.YAMLError, match="duplicate key 'operator'"):
        validate_yaml.load(text)


def test_merge_keys_custom_tags_and_separate_documents_still_load():
    text = (
        "base: &base {a: 1}\n"
        "first:\n  <<: *base\n  a: 2\n"
        "second:\n  <<: *base\n"
        "value: !vault |\n  secret\n"
        "---\n"
        "first: 1\n"
    )
    assert len(validate_yaml.load(text)) == 2
