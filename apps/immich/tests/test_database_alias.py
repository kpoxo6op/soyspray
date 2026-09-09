import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DATABASE = ROOT / "apps/immich/database"
CATALOG = ROOT / "argocd/catalog"


def render(path: Path) -> list[dict]:
    result = subprocess.run(
        ["kubectl", "kustomize", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(yaml.safe_load_all(result.stdout))


def test_explicit_alias_renders_the_active_a_service() -> None:
    old = render(DATABASE / "immich-db-active/overlays/active-a")
    explicit = render(DATABASE / "alias")

    assert explicit == old
    assert (explicit[0]["kind"], explicit[0]["metadata"]["name"]) == (
        "Service",
        "immich-db-active",
    )


def test_direct_application_uses_the_explicit_alias_path() -> None:
    application = yaml.safe_load((CATALOG / "immich-db-alias.yaml").read_text())
    source = application["spec"]["sources"][0]

    assert application["kind"] == "Application"
    assert application["metadata"]["name"] == "immich-db-active-a"
    assert source == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "main",
        "path": "apps/immich/database/alias",
    }
