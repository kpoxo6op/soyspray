from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_KINDS = {
    "KongPlugin",
    "KongClusterPlugin",
    "KongConsumer",
    "KongConsumerGroup",
    "KongIngress",
    "TCPIngress",
    "UDPIngress",
    "Secret",
}


def yaml_docs(path: Path):
    return [doc for doc in yaml.safe_load_all(path.read_text()) if isinstance(doc, dict)]


def test_no_forbidden_kong_resource_kinds_in_goal_002():
    offenders = []
    for path in (ROOT / "platform/kong").rglob("*.yaml"):
        for doc in yaml_docs(path):
            if doc.get("kind") in FORBIDDEN_KINDS:
                offenders.append((str(path.relative_to(ROOT)), doc["kind"]))
    assert offenders == []


def test_no_auth_or_rate_limit_plugins_in_goal_002():
    forbidden = ["key-auth", "jwt", "acl", "rate-limiting"]
    offenders = []
    for path in (ROOT / "platform/kong").rglob("*"):
        if "gateway-api/crds" in path.as_posix():
            continue
        if path.is_file() and path.suffix in {".yaml", ".yml"}:
            content = path.read_text().lower()
            for term in forbidden:
                if term in content:
                    offenders.append((str(path.relative_to(ROOT)), term))
    assert offenders == []
