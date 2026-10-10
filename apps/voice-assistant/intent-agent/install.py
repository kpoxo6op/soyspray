"""Install only this image's component, preserving all other HA configuration."""

import argparse
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path


def install(source, config, revision="development"):
    source, config = Path(source), Path(config)
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest.get("domain") != "gi_voice" or manifest.get("requirements"):
        raise ValueError("The packaged component contract is invalid")
    parent = config / "custom_components"
    target = parent / "gi_voice"
    state = config / ".gi_voice"
    previous = state / "previous"
    if parent.is_symlink() or target.is_symlink() or state.is_symlink() or previous.is_symlink():
        raise ValueError("Refusing a symlink outside the component scope")
    parent.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".gi-voice-stage-", dir=state) as work:
        staged = Path(work) / "gi_voice"
        shutil.copytree(source, staged)
        manifest["version"] = "0.1.0+" + revision
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        marker = Path(work) / "installed.json"
        marker.write_text(json.dumps({"source_revision": revision}) + "\n")
        if previous.exists():
            shutil.rmtree(previous)
        moved = False
        replaced = False
        try:
            if target.exists():
                target.rename(previous)
                moved = True
            staged.rename(target)
            replaced = True
            marker.replace(state / "installed.json")
        except BaseException:
            if replaced:
                target.rename(staged)
            if moved:
                previous.rename(target)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="/component")
    parser.add_argument("--config-dir", default="/config")
    parser.add_argument("--revision", default=os.environ.get("SOURCE_REVISION", "development"))
    args = parser.parse_args()
    try:
        install(args.source, args.config_dir, args.revision)
    except Exception as error:
        # This optional component must never prevent the main HA container from starting.
        logging.error("GI Flex was not installed (%s); verify installed.json", type(error).__name__)
