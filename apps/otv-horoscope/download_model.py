"""Bake the pinned public Whisper model into the image; nothing downloads at runtime."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


def download(url: str, checksum: str, destination: Path) -> None:
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=300) as response, destination.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != checksum:
        destination.unlink()
        raise ValueError(f"Checksum mismatch for {destination.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("models.lock.json").read_text())
    for name, model in lock.items():
        target = args.output / name
        target.mkdir(parents=True, exist_ok=True)
        base = f"https://huggingface.co/{model['repository']}/resolve/{model['revision']}"
        for filename, checksum in model["files"].items():
            download(f"{base}/{filename}", checksum, target / filename)


if __name__ == "__main__":
    main()
