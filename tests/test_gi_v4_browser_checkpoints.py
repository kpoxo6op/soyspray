from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/gi_v4_browser_checkpoints.py"
V3_DRIVER = ROOT / "scripts/train_gi_v3_colab.py"


def _load(path: Path, name: str) -> ModuleType:
    assert path.is_file(), f"missing {path.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_helper() -> ModuleType:
    return _load(SCRIPT, "test_gi_v4_browser_checkpoints")


def test_v4_browser_paths_and_archive_allowlist_are_versioned() -> None:
    helper = load_helper()

    assert helper.CANDIDATE == "gi-v4"
    assert helper.WORKSPACE == Path("/content/gi-v4")
    assert helper.CHECKPOINT_DIR == Path("/content/gi-v4-checkpoints")
    assert helper.IMPORT_DIR == Path("/content/gi-v4-import")
    assert helper.TRANSFER_DIR == Path("/content/gi-v4-transfer")
    assert helper.MANIFEST_BASENAME == "gi-v4-manifest.json"
    assert [spec.archive for spec in helper.STAGES.values()] == [
        "gi-v4-generated-clips.tar",
        "gi-v4-features.tar",
        "gi-v4-onnx.tar",
        "gi-v4-final-bundle.tar",
    ]
    assert helper.TRAINER.CANDIDATE == "gi-v4"


def test_raw_v3_transfer_name_is_rejected(tmp_path: Path) -> None:
    helper = load_helper()
    imported = tmp_path / "import"
    imported.mkdir()
    (imported / "gi-v3-generated-clips.tar.transfer.sha256").write_text(
        "0" * 64 + "  gi-v3-generated-clips.tar.part-0000\n"
    )

    with pytest.raises(RuntimeError, match="Unexpected transfer file"):
        helper._validate_import_tree(imported)


def test_renamed_v3_checkpoint_fails_v4_provenance(tmp_path: Path) -> None:
    helper = load_helper()
    v3 = _load(V3_DRIVER, "v3_for_v4_transfer_rejection")
    workspace = tmp_path / "v3-workspace"
    checkpoint = tmp_path / "v3.tar"
    source = workspace / "stage/data.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"v3")
    v3._archive_checkpoint(checkpoint, workspace, (Path("stage/data.bin"),), "generate")

    imported = tmp_path / "import"
    imported.mkdir()
    spec = helper.STAGES["generate"]
    part = imported / f"{spec.archive}.part-0000"
    sidecar = imported / spec.sidecar
    shutil.copyfile(checkpoint, part)
    shutil.copyfile(v3._checkpoint_manifest(checkpoint), sidecar)

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    (imported / spec.transfer_manifest).write_text(
        f"{digest(sidecar)}  {sidecar.name}\n{digest(part)}  {part.name}\n"
    )

    with pytest.raises(RuntimeError, match="trainer provenance"):
        helper._restore_one("generate", tmp_path / "checkpoints", imported)


def test_browser_provenance_binds_v4_helper_and_trainer() -> None:
    helper = load_helper()
    record = helper.provenance()

    assert record == {
        "helper_sha256": helper.sha256(SCRIPT),
        "trainer_sha256": helper.sha256(helper.TRAINER.DRIVER),
    }
    assert json.loads(json.dumps(record)) == record
