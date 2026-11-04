from __future__ import annotations

import yaml
from conftest import load_yaml

REVISION = "1a5774e3d8dbd7a7c8f7ce75be6248cda8143c5d"
TREE = "13c1b9760c0fe8fdae1800ea3eb16d7129f6b3ea"


def _deployment_spec() -> dict:
    return load_yaml("apps/home-assistant/manifests/deployment.yaml")["spec"]["template"]["spec"]


def test_mercury_integration_is_installed_from_a_verified_revision() -> None:
    init_containers = {item["name"]: item for item in _deployment_spec()["initContainers"]}
    script = init_containers["install-mercury-energy"]["command"][-1]

    assert f'revision="{REVISION}"' in script
    assert f'expected_tree="{TREE}"' in script
    assert 'test "$(git -C "${tmp_dir}" rev-parse FETCH_HEAD)" = "${revision}"' in script
    assert "rev-parse FETCH_HEAD:custom_components/mercury_co_nz" in script
    assert 'install_dir="/config/custom_components/mercury_co_nz"' in script
    # Only the integration's own folder is replaced; other components stay.
    assert 'rm -rf "${install_dir}"' in script
    assert "rm -rf /config/custom_components\n" not in script


def test_power_is_a_page_of_the_home_dashboard() -> None:
    bootstrap = load_yaml("apps/home-assistant/manifests/configmap-bootstrap.yaml")["data"]
    init_containers = {item["name"]: item for item in _deployment_spec()["initContainers"]}
    copy_script = init_containers["bootstrap-config"]["command"][-1]
    configuration = bootstrap["configuration.yaml"]

    assert "cp /bootstrap/home-dashboard.yaml /config/dashboards/home.yaml" in copy_script
    assert "currency: NZD" in configuration
    assert "filename: dashboards/home.yaml" in configuration
    # Card resources stay in storage mode so existing UI resources keep working.
    assert "resource_mode" not in configuration

    views = {v["path"]: v for v in yaml.safe_load(bootstrap["home-dashboard.yaml"])["views"]}
    cards = [card for section in views["power"]["sections"] for card in section["cards"]]
    card_types = {card["type"] for card in cards}
    assert {
        "custom:mercury-energy-usage-card",
        "custom:mercury-energy-weekly-summary-card",
        "custom:mercury-energy-monthly-summary-card",
    } <= card_types
    entities = {card["entity"] for card in cards if "entity" in card}
    assert all(entity.startswith(("sensor.mercury_nz_", "sensor.power_")) for entity in entities)
