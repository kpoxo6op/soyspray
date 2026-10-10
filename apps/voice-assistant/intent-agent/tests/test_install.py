"""The existing HA installers do not own this component's scoped replacement."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from install import install

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/gi_voice"


def test_install_preserves_private_and_unrelated_component_files(tmp_path):
    config = tmp_path / "config"
    (config / ".storage").mkdir(parents=True)
    (config / ".storage/private").write_text("private-state")
    other = config / "custom_components/other"
    other.mkdir(parents=True)
    (other / "keep").write_text("unrelated")
    install(SOURCE, config)
    assert (config / ".storage/private").read_text() == "private-state"
    assert (other / "keep").read_text() == "unrelated"
    assert (config / "custom_components/gi_voice/manifest.json").exists()


def test_failed_replacement_restores_previous_component(tmp_path):
    config = tmp_path / "config"
    target = config / "custom_components/gi_voice"
    target.mkdir(parents=True)
    (target / "old").write_text("working-source")
    rename = Path.rename

    def fail_stage(path, destination):
        if ".gi-voice-stage-" in str(path):
            raise OSError("Simulated storage failure")
        return rename(path, destination)

    with patch.object(Path, "rename", fail_stage), pytest.raises(OSError):
        install(SOURCE, config)
    assert (target / "old").read_text() == "working-source"


def test_symlink_cannot_redirect_installation(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (config / "custom_components").symlink_to(outside)
    with pytest.raises(ValueError):
        install(SOURCE, config)
    assert not list(outside.iterdir())


def test_two_installs_leave_only_one_discoverable_domain(tmp_path):
    install(SOURCE, tmp_path, "first")
    install(SOURCE, tmp_path, "second")
    manifests = list((tmp_path / "custom_components").glob("*/manifest.json"))
    assert len(manifests) == 1
    assert json.loads(manifests[0].read_text())["version"] == "0.1.0+second"
    assert (tmp_path / ".gi_voice/previous/manifest.json").exists()
    assert (
        json.loads((tmp_path / ".gi_voice/installed.json").read_text())["source_revision"]
        == "second"
    )


def test_optional_installer_failure_allows_ha_to_start(tmp_path):
    other = tmp_path / "private"
    other.write_text("preserved")
    result = subprocess.run(
        [
            sys.executable,
            str(SOURCE.parents[1] / "install.py"),
            "--source",
            str(tmp_path / "missing"),
            "--config-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "not installed" in result.stderr
    assert other.read_text() == "preserved"
