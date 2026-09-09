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


def identity(resource: dict) -> tuple[str, str]:
    return resource["kind"], resource["metadata"]["name"]


def test_explicit_production_renders_only_the_existing_objects() -> None:
    explicit = sorted(render(DATABASE / "production"), key=identity)
    assert [identity(resource) for resource in explicit] == [
        ("Cluster", "immich-db-a"),
        ("ScheduledBackup", "immich-db-daily-a"),
        ("Secret", "immich-app-secret-a"),
    ]
    cluster = next(resource for resource in explicit if resource["kind"] == "Cluster")
    assert cluster["spec"]["bootstrap"]["initdb"]["secret"]["name"] == ("immich-app-secret-a")
    assert cluster["spec"]["imageName"] == ("ghcr.io/tensorchord/cloudnative-pgvecto.rs:16-v0.3.0")


def test_direct_application_uses_the_explicit_production_path() -> None:
    application = yaml.safe_load((CATALOG / "immich-db.yaml").read_text())
    source = application["spec"]["sources"][0]

    assert application["kind"] == "Application"
    assert application["metadata"]["name"] == "immich-db-a-initdb"
    assert source == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "main",
        "path": "apps/immich/database/production",
    }
