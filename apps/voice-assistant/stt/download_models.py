"""Bake verified public models into an image, with no runtime downloading."""

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path


def download(url, checksum, destination):
    """Reject corrupted or changed upstream objects before using them."""
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != checksum:
        destination.unlink()
        raise ValueError("Model checksum mismatch")


def extract_models(archive, output, directory, files):
    """Copy only the expected regular model files; never extract archive paths."""
    expected = {directory + "/" + name: output / directory / name for name in files}
    found = set()
    with tarfile.open(archive, "r:bz2") as tar:
        for member in tar:
            if member.name not in expected:
                continue
            if not member.isfile() or member.name in found:
                raise ValueError("Unexpected model archive member")
            destination = expected[member.name]
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, destination.open("wb") as out:
                shutil.copyfileobj(source, out)
            found.add(member.name)
    if found != set(expected):
        raise ValueError("Missing model archive members")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("models.lock.json").read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ("base.en", "small.en"):
        destination = args.output / name
        destination.mkdir(exist_ok=True)
        for filename, item in lock[name]["files"].items():
            download(item["url"], item["sha256"], destination / filename)
    item = lock["parakeet"]
    with tempfile.TemporaryDirectory() as work:
        archive = Path(work) / "parakeet.tar.bz2"
        download(item["url"], item["sha256"], archive)
        extract_models(archive, args.output, item["directory"], item["files"])


if __name__ == "__main__":
    main()
