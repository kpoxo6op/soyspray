"""Install only this image's component, preserving all other HA configuration."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path


def install(source, config):
    source, config = Path(source), Path(config)
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest.get("domain") != "gi_voice" or manifest.get("requirements"):
        raise ValueError("The packaged component contract is invalid")
    parent = config / "custom_components"
    target = parent / "gi_voice"
    previous = parent / ".gi_voice-previous"
    if parent.is_symlink() or target.is_symlink() or previous.is_symlink():
        raise ValueError("Refusing a symlink outside the component scope")
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".gi-voice-stage-", dir=parent) as work:
        staged = Path(work) / "gi_voice"
        shutil.copytree(source, staged)
        if previous.exists():
            shutil.rmtree(previous)
        moved = False
        try:
            if target.exists():
                target.rename(previous)
                moved = True
            staged.rename(target)
        except BaseException:
            if moved and not target.exists():
                previous.rename(target)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="/component")
    parser.add_argument("--config-dir", default="/config")
    args = parser.parse_args()
    install(args.source, args.config_dir)
