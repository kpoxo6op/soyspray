"""Protect downloaded artifacts and prevent archive writes outside model scope."""

import hashlib
import io
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from download_models import download, extract_models


def archive(path, members):
    with tarfile.open(path, "w:bz2") as tar:
        for name, symlink in members:
            member = tarfile.TarInfo(name)
            member.size = 3
            if symlink:
                member.type, member.linkname = tarfile.SYMTYPE, "/etc/passwd"
            tar.addfile(member, None if symlink else io.BytesIO(b"abc"))


def test_changed_download_is_removed(tmp_path):
    source, target = tmp_path / "upstream", tmp_path / "model"
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        download(source.as_uri(), hashlib.sha256(b"expected").hexdigest(), target)
    assert not target.exists()


def test_only_regular_expected_models_are_copied(tmp_path):
    source = tmp_path / "models.tar.bz2"
    archive(source, [("../../escape", False), ("model/encoder", False)])
    extract_models(source, tmp_path / "output", "model", ["encoder"])
    assert (tmp_path / "output/model/encoder").read_bytes() == b"abc"
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("members", [[], [("model/encoder", True)]])
def test_missing_or_linked_model_fails(tmp_path, members):
    source = tmp_path / "models.tar.bz2"
    archive(source, members)
    with pytest.raises(ValueError):
        extract_models(source, tmp_path / "output", "model", ["encoder"])
