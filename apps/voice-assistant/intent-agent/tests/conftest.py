"""Test with the real HA custom component loader and deployed HA version."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield
