from __future__ import annotations

import subprocess

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
REMOVED_DEMO_APPS = ("battlemap", "jira")


def test_retired_media_application_sources_are_absent() -> None:
    for app in REMOVED_MEDIA_APPS:
        assert not (ROOT / "playbooks/argocd/applications/media" / app).exists()
        assert not (ROOT / "roles/apps" / app).exists()


def test_retired_demo_application_sources_are_absent() -> None:
    for app in REMOVED_DEMO_APPS:
        assert not (ROOT / "playbooks/argocd/applications/workloads" / app).exists()
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
