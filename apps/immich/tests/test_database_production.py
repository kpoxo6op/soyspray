import copy
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


def old_production_with_a_suffix() -> list[dict]:
    resources = copy.deepcopy(render(DATABASE / "immich-db/overlays/initdb"))
    for resource in resources:
        name = resource["metadata"]["name"]
        resource["metadata"]["name"] = f"{name}-a"
        if resource["kind"] == "Cluster":
            resource["spec"]["bootstrap"]["initdb"]["secret"]["name"] += "-a"
        if resource["kind"] == "ScheduledBackup":
            resource["spec"]["cluster"]["name"] += "-a"
    return resources


def test_explicit_production_renders_the_generated_a_objects() -> None:
    old = sorted(old_production_with_a_suffix(), key=identity)
    explicit = sorted(render(DATABASE / "production"), key=identity)

    assert explicit == old
    assert [identity(resource) for resource in explicit] == [
        ("Cluster", "immich-db-a"),
        ("ScheduledBackup", "immich-db-daily-a"),
        ("Secret", "immich-app-secret-a"),
    ]


def test_transitional_generator_uses_the_explicit_production_path() -> None:
    application_set = yaml.safe_load((CATALOG / "immich-db.yaml").read_text())
    source = application_set["spec"]["template"]["spec"]["sources"][0]

    assert source == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "main",
        "path": "apps/immich/database/production",
    }
