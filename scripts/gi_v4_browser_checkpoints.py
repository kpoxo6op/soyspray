#!/usr/bin/env python3
"""Run GI v4 with checksum-verified browser-transfer checkpoints."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve()
COMMON_HELPER = SCRIPT.with_name("gi_v3_browser_checkpoints.py")
TRAINER_PATH = SCRIPT.with_name("train_gi_v4_colab.py")
CANDIDATE = "gi-v4"
MANIFEST_BASENAME = f"{CANDIDATE}-manifest.json"
CONTENT_ROOT = Path("/content")
WORKSPACE = CONTENT_ROOT / CANDIDATE
CHECKPOINT_DIR = CONTENT_ROOT / f"{CANDIDATE}-checkpoints"
IMPORT_DIR = CONTENT_ROOT / f"{CANDIDATE}-import"
TRANSFER_DIR = CONTENT_ROOT / f"{CANDIDATE}-transfer"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load(COMMON_HELPER, "gi_v4_browser_shared_base")
TRAINER = _load(TRAINER_PATH, "gi_v4_browser_trainer")
STAGES = {
    "generate": BASE.StageSpec("generate", f"{CANDIDATE}-generated-clips.tar"),
    "augment": BASE.StageSpec("augment", f"{CANDIDATE}-features.tar"),
    "train": BASE.StageSpec("train", f"{CANDIDATE}-onnx.tar"),
    "finish": BASE.StageSpec("bundle", f"{CANDIDATE}-final-bundle.tar"),
}

BASE.SCRIPT = SCRIPT
BASE.CANDIDATE = CANDIDATE
BASE.TRAINER_PATH = TRAINER_PATH
BASE.TRAINER = TRAINER
BASE.MANIFEST_BASENAME = MANIFEST_BASENAME
BASE.WORKSPACE = WORKSPACE
BASE.CHECKPOINT_DIR = CHECKPOINT_DIR
BASE.IMPORT_DIR = IMPORT_DIR
BASE.TRANSFER_DIR = TRANSFER_DIR
BASE.STAGES = STAGES


def __getattr__(name: str) -> object:
    return getattr(BASE, name)


def main() -> int:
    return BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
