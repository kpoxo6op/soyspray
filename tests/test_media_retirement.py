from __future__ import annotations

import subprocess

import yaml
from conftest import ROOT

REMOVED_MEDIA_APPS = (
    "jellyfin",
    "plex",
    "prowlarr",
    "radarr",
    "sonarr",
    "streamlink",
    "threadfin",
)

BOOK_WORKFLOW_APPS = ("qbittorrent", "lazylibrarian", "booklore")


def test_retired_media_application_sources_are_absent() -> None:
    for app in REMOVED_MEDIA_APPS:
        assert not (ROOT / "playbooks/argocd/applications/media" / app).exists()
        assert not (ROOT / "roles/apps" / app).exists()


def test_book_workflow_remains_renderable() -> None:
    for app in BOOK_WORKFLOW_APPS:
        path = ROOT / "playbooks/argocd/applications/media" / app
        result = subprocess.run(
            ["kubectl", "kustomize", str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "apiVersion:" in result.stdout


def test_lazylibrarian_keeps_qbittorrent_download_path() -> None:
    config = (
        ROOT / "playbooks/argocd/applications/media/lazylibrarian/initial-config-configmap.yaml"
    ).read_text()
    assert "tor_downloader_qbittorrent = True" in config
    assert "qbittorrent_host = qbittorrent.media.svc.cluster.local" in config


def test_cleanup_quiesces_applications_before_deleting_resources() -> None:
    tasks = yaml.safe_load((ROOT / "roles/apps/retired-media-cleanup/tasks/main.yml").read_text())
    task_names = [task["name"] for task in tasks]
    assert task_names.index("Quiesce retired applications before removal") < task_names.index(
        "Remove retired Argo applications and their managed resources"
    )
    assert task_names.index(
        "Remove retired Argo applications and their managed resources"
    ) < task_names.index("Remove resources orphaned by applications without finalizers")


def test_cleanup_deletes_only_dedicated_retired_media_data() -> None:
    defaults = yaml.safe_load(
        (ROOT / "roles/apps/retired-media-cleanup/defaults/main.yml").read_text()
    )
    assert set(defaults["retired_media_applications"]) == set(REMOVED_MEDIA_APPS)
    assert "PersistentVolumeClaim" in defaults["retired_media_resource_kinds"]
    serialized = yaml.safe_dump(defaults)
    assert "media-downloads" not in serialized
    assert "qbittorrent" not in serialized
    assert "lazylibrarian" not in serialized
    assert "booklore" not in serialized
