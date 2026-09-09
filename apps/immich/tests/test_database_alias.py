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


def test_transitional_generator_uses_the_explicit_alias_path() -> None:
    application_set = yaml.safe_load((CATALOG / "immich-db-alias.yaml").read_text())
    source = application_set["spec"]["template"]["spec"]["sources"][0]

    assert source == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "main",
        "path": "apps/immich/database/alias",
    }
