from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_KONG_KINDS = {
    "GatewayClass",
    "Gateway",
    "HTTPRoute",
    "KongPlugin",
    "KongClusterPlugin",
    "KongConsumer",
    "KongIngress",
    "TCPIngress",
    "UDPIngress",
}


def platform_yaml_files():
    return sorted(
        path
        for path in (ROOT / "platform").rglob("*")
        if path.suffix in {".yaml", ".yml"}
        and "platform/kong" not in str(path.relative_to(ROOT))
    )


def test_no_kong_runtime_resources_in_goal_001_platform_manifests():
    found = []
    for path in platform_yaml_files():
        for doc in yaml.safe_load_all(path.read_text()):
            if isinstance(doc, dict) and doc.get("kind") in FORBIDDEN_KONG_KINDS:
                found.append((str(path.relative_to(ROOT)), doc["kind"]))
    assert found == []


def test_no_kong_plugin_text_in_platform_manifests():
    offenders = [
        str(path.relative_to(ROOT))
        for path in platform_yaml_files()
        if not str(path.relative_to(ROOT)).startswith("platform/change-control/")
        if "KongPlugin" in path.read_text() or "KongConsumer" in path.read_text()
    ]
    assert offenders == []
