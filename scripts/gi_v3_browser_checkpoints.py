#!/usr/bin/env python3
"""Run GI v3 with checksum-verified browser-transfer checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

SCRIPT = Path(__file__).resolve()
TRAINER_PATH = SCRIPT.with_name("train_gi_v3_colab.py")
CONTENT_ROOT = Path("/content")
WORKSPACE = CONTENT_ROOT / "gi-v3"
CHECKPOINT_DIR = CONTENT_ROOT / "gi-v3-checkpoints"
IMPORT_DIR = CONTENT_ROOT / "gi-v3-import"
TRANSFER_DIR = CONTENT_ROOT / "gi-v3-transfer"
CHUNK_BYTES = 64 * 1024**2


def _load_trainer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("train_gi_v3_colab", TRAINER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load GI v3 trainer: {TRAINER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRAINER = _load_trainer()


class StageSpec(NamedTuple):
    trainer_stage: str
    archive: str

    @property
    def sidecar(self) -> str:
        return f"{self.archive}.json"

    @property
    def transfer_manifest(self) -> str:
        return f"{self.archive}.transfer.sha256"


STAGES = {
    "generate": StageSpec("generate", "gi-v3-generated-clips.tar"),
    "augment": StageSpec("augment", "gi-v3-features.tar"),
    "train": StageSpec("train", "gi-v3-onnx.tar"),
    "finish": StageSpec("bundle", "gi-v3-final-bundle.tar"),
}
TRAINING_STAGES = ("generate", "augment", "train")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            stream.write(value)
            temporary_name = stream.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with (
            source.open("rb") as input_stream,
            tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as output_stream,
        ):
            shutil.copyfileobj(input_stream, output_stream)
            temporary_name = output_stream.name
        os.replace(temporary_name, destination)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _safe_regular_file(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlink transfer file: {path}")
    if not path.is_file():
        raise RuntimeError(f"Missing transfer file: {path}")


def _checkpoint_valid(checkpoint_dir: Path, stage: str) -> bool:
    spec = STAGES[stage]
    archive = checkpoint_dir / spec.archive
    sidecar = checkpoint_dir / spec.sidecar
    if archive.is_symlink() or sidecar.is_symlink():
        raise RuntimeError(f"Refusing symlinked {stage} checkpoint")
    return TRAINER._checkpoint_valid(archive, spec.trainer_stage)


def _bundled_manifest_sha256(archive: Path) -> str:
    with tarfile.open(archive) as bundle:
        try:
            member = bundle.getmember("gi-v3-manifest.json")
        except KeyError as error:
            raise RuntimeError(f"Final bundle has no GI v3 manifest: {archive}") from error
        if not member.isfile():
            raise RuntimeError(f"Final bundle manifest is not a file: {archive}")
        stream = bundle.extractfile(member)
        if stream is None:
            raise RuntimeError(f"Cannot read final bundle manifest: {archive}")
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024**2), b""):
            digest.update(block)
        return digest.hexdigest()


def _safe_basename(name: str) -> None:
    if not name or name in {".", ".."} or Path(name).name != name or "/" in name or "\\" in name:
        raise RuntimeError(f"Transfer manifest entry is not a safe basename: {name!r}")


def provenance() -> dict[str, str]:
    return {
        "helper_sha256": sha256(SCRIPT),
        "trainer_sha256": sha256(TRAINER.DRIVER),
    }


def require_local_boundaries(
    workspace: Path,
    checkpoint_dir: Path,
    import_dir: Path,
    transfer_dir: Path,
    *,
    content_root: Path = CONTENT_ROOT,
) -> None:
    if not content_root.is_dir():
        raise RuntimeError(f"Missing Colab content root: {content_root}")
    expected = {
        "workspace": content_root / "gi-v3",
        "checkpoint_dir": content_root / "gi-v3-checkpoints",
        "import_dir": content_root / "gi-v3-import",
        "transfer_dir": content_root / "gi-v3-transfer",
    }
    supplied = {
        "workspace": workspace,
        "checkpoint_dir": checkpoint_dir,
        "import_dir": import_dir,
        "transfer_dir": transfer_dir,
    }
    for name, path in supplied.items():
        if path.is_symlink():
            raise RuntimeError(f"{name} must not be a symlink: {path}")
        if path.resolve() != expected[name].resolve():
            raise RuntimeError(f"{name} must be {expected[name]}; got {path}")


def read_sha256sums(path: Path) -> dict[str, str]:
    _safe_regular_file(path)
    entries: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if "  " not in raw:
            raise RuntimeError(f"Invalid SHA256SUMS line {line_number}: {raw!r}")
        digest, name = raw.split("  ", 1)
        _safe_basename(name)
        if not SHA256_RE.fullmatch(digest):
            raise RuntimeError(f"Invalid SHA-256 on line {line_number}: {digest!r}")
        if name in entries:
            raise RuntimeError(f"Duplicate SHA256SUMS entry: {name}")
        entries[name] = digest
    if not entries:
        raise RuntimeError(f"Empty SHA256SUMS manifest: {path}")
    return entries


def _remove_previous_parts(transfer_dir: Path, archive: str) -> None:
    for path in transfer_dir.glob(f"{archive}.part-*"):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Refusing unsafe old transfer part: {path}")
        path.unlink()


def _combined_parts(parts: list[Path]) -> tuple[int, str]:
    digest = hashlib.sha256()
    byte_count = 0
    for part in parts:
        with part.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                digest.update(block)
                byte_count += len(block)
    return byte_count, digest.hexdigest()


def _existing_transfer(
    stage: str, checkpoint_dir: Path, transfer_dir: Path
) -> tuple[Path, ...] | None:
    spec = STAGES[stage]
    manifest = transfer_dir / spec.transfer_manifest
    if not manifest.exists():
        return None
    entries, part_names = _validate_transfer_set(stage, transfer_dir)
    archive = checkpoint_dir / spec.archive
    sidecar = checkpoint_dir / spec.sidecar
    parts = [transfer_dir / name for name in part_names]
    size, digest = _combined_parts(parts)
    same = (
        sha256(transfer_dir / spec.sidecar) == sha256(sidecar)
        and size == archive.stat().st_size
        and digest == sha256(archive)
    )
    if stage == "finish":
        source_manifest = checkpoint_dir / "gi-v3-manifest.json"
        same = same and sha256(transfer_dir / source_manifest.name) == sha256(source_manifest)
    if not same:
        raise RuntimeError(
            f"Existing transfer set differs from {stage} checkpoint; preserve it and use a clean transfer directory"
        )
    return tuple(transfer_dir / name for name in entries) + (manifest,)


def pack_checkpoint(
    stage: str,
    checkpoint_dir: Path,
    transfer_dir: Path,
    *,
    chunk_bytes: int = CHUNK_BYTES,
) -> tuple[Path, ...]:
    if stage not in STAGES:
        raise ValueError(f"Unknown browser checkpoint stage: {stage}")
    if chunk_bytes <= 0:
        raise ValueError("chunk_bytes must be positive")
    if transfer_dir.is_symlink():
        raise RuntimeError(f"Transfer directory must not be a symlink: {transfer_dir}")
    transfer_dir.mkdir(parents=True, exist_ok=True)
    for child in transfer_dir.iterdir():
        if child.is_symlink():
            raise RuntimeError(f"Refusing symlink in transfer directory: {child}")

    spec = STAGES[stage]
    archive = checkpoint_dir / spec.archive
    sidecar = checkpoint_dir / spec.sidecar
    _safe_regular_file(archive)
    _safe_regular_file(sidecar)
    if not TRAINER._checkpoint_valid(archive, spec.trainer_stage):
        raise RuntimeError(f"Checkpoint failed trainer provenance validation: {archive}")
    if stage == "finish":
        source_manifest = checkpoint_dir / "gi-v3-manifest.json"
        _safe_regular_file(source_manifest)
        if sha256(source_manifest) != _bundled_manifest_sha256(archive):
            raise RuntimeError("Separate GI v3 manifest differs from the final bundle")

    existing = _existing_transfer(stage, checkpoint_dir, transfer_dir)
    if existing is not None:
        return existing

    if transfer_dir.resolve().is_relative_to(CONTENT_ROOT.resolve()):
        free = shutil.disk_usage(transfer_dir).free
        if free < archive.stat().st_size + 2 * 1024**3:
            raise RuntimeError("Browser checkpoint split needs archive size plus 2 GiB free")

    _remove_previous_parts(transfer_dir, spec.archive)
    copied: list[Path] = []
    destination_sidecar = transfer_dir / spec.sidecar
    _atomic_copy(sidecar, destination_sidecar)
    copied.append(destination_sidecar)

    if stage == "finish":
        destination_manifest = transfer_dir / source_manifest.name
        _atomic_copy(source_manifest, destination_manifest)
        copied.append(destination_manifest)

    with archive.open("rb") as source:
        index = 0
        while block := source.read(chunk_bytes):
            part = transfer_dir / f"{spec.archive}.part-{index:04d}"
            temporary_name: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=transfer_dir,
                    prefix=f".{part.name}.",
                    delete=False,
                ) as output:
                    output.write(block)
                    temporary_name = output.name
                os.replace(temporary_name, part)
            finally:
                if temporary_name is not None:
                    Path(temporary_name).unlink(missing_ok=True)
            copied.append(part)
            index += 1
    if not any(".part-" in path.name for path in copied):
        raise RuntimeError(f"Checkpoint archive is empty: {archive}")

    manifest = transfer_dir / spec.transfer_manifest
    lines = [f"{sha256(path)}  {path.name}\n" for path in copied]
    _atomic_text(manifest, "".join(lines))
    return (*copied, manifest)


def _part_names(spec: StageSpec, entries: dict[str, str]) -> list[str]:
    prefix = f"{spec.archive}.part-"
    parts = [name for name in entries if name.startswith(prefix)]
    expected = [f"{prefix}{index:04d}" for index in range(len(parts))]
    if parts != expected or not parts:
        raise RuntimeError(f"Transfer parts for {spec.archive} must be consecutive from part-0000")
    return parts


def _validate_transfer_set(stage: str, import_dir: Path) -> tuple[dict[str, str], list[str]]:
    spec = STAGES[stage]
    manifest = import_dir / spec.transfer_manifest
    entries = read_sha256sums(manifest)
    expected_fixed = {spec.sidecar}
    if stage == "finish":
        expected_fixed.add("gi-v3-manifest.json")
    parts = _part_names(spec, entries)
    if set(entries) != expected_fixed | set(parts):
        raise RuntimeError(f"Unexpected transfer manifest entries for {stage}")
    for name, expected in entries.items():
        path = import_dir / name
        _safe_regular_file(path)
        if sha256(path) != expected:
            raise RuntimeError(f"SHA-256 mismatch for transfer file: {path}")
    return entries, parts


def _validate_import_tree(import_dir: Path) -> set[str]:
    if import_dir.is_symlink():
        raise RuntimeError(f"Import directory must not be a symlink: {import_dir}")
    if not import_dir.exists():
        return set()
    if not import_dir.is_dir():
        raise RuntimeError(f"Import path is not a directory: {import_dir}")
    present_manifests = {
        stage for stage, spec in STAGES.items() if (import_dir / spec.transfer_manifest).exists()
    }
    allowed = {STAGES[stage].transfer_manifest for stage in present_manifests}
    for stage in present_manifests:
        entries, _ = _validate_transfer_set(stage, import_dir)
        allowed.update(entries)
    for path in import_dir.iterdir():
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlink transfer file: {path}")
        if not path.is_file() or path.name not in allowed:
            raise RuntimeError(f"Unexpected transfer file: {path.name}")
    return present_manifests


def _restore_one(stage: str, checkpoint_dir: Path, import_dir: Path) -> None:
    spec = STAGES[stage]
    archive = checkpoint_dir / spec.archive
    if _checkpoint_valid(checkpoint_dir, stage):
        return
    entries, parts = _validate_transfer_set(stage, import_dir)
    sidecar_source = import_dir / spec.sidecar
    try:
        record = json.loads(sidecar_source.read_text(encoding="utf-8"))
        expected_bytes = int(record["bytes"])
        expected_sha256 = record["sha256"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Invalid checkpoint sidecar: {sidecar_source}") from error
    if (
        expected_bytes < 0
        or not isinstance(expected_sha256, str)
        or not SHA256_RE.fullmatch(expected_sha256)
    ):
        raise RuntimeError(f"Invalid checkpoint sidecar: {sidecar_source}")

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{stage}-restore-", dir=checkpoint_dir) as temporary:
        staging_dir = Path(temporary)
        staging_archive = staging_dir / spec.archive
        digest = hashlib.sha256()
        byte_count = 0
        with staging_archive.open("wb") as output:
            for name in parts:
                source = import_dir / name
                with source.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024**2), b""):
                        output.write(block)
                        digest.update(block)
                        byte_count += len(block)
        staging_sidecar = staging_dir / spec.sidecar
        shutil.copyfile(sidecar_source, staging_sidecar)
        if byte_count != expected_bytes or digest.hexdigest() != expected_sha256:
            raise RuntimeError(f"Reassembled checkpoint SHA-256 or size mismatch: {archive}")
        if not TRAINER._checkpoint_valid(staging_archive, spec.trainer_stage):
            raise RuntimeError(f"Restored checkpoint failed trainer provenance: {archive}")
        os.replace(staging_archive, archive)
        os.replace(staging_sidecar, checkpoint_dir / spec.sidecar)


def _restore_finish_manifest(checkpoint_dir: Path, import_dir: Path) -> None:
    destination = checkpoint_dir / "gi-v3-manifest.json"
    source = import_dir / destination.name
    expected = _bundled_manifest_sha256(checkpoint_dir / STAGES["finish"].archive)
    if destination.is_file() and not destination.is_symlink() and sha256(destination) == expected:
        return
    _safe_regular_file(source)
    if sha256(source) != expected:
        raise RuntimeError("Imported GI v3 manifest differs from the final bundle")
    _atomic_copy(source, destination)


def restore_through(through: str, checkpoint_dir: Path, import_dir: Path) -> tuple[str, ...]:
    if through not in STAGES:
        raise ValueError(f"Unknown browser checkpoint stage: {through}")
    _validate_import_tree(import_dir)
    order = (*TRAINING_STAGES, "finish")
    restored: list[str] = []
    for stage in order[: order.index(through) + 1]:
        spec = STAGES[stage]
        if not _checkpoint_valid(checkpoint_dir, stage):
            if not (import_dir / spec.transfer_manifest).is_file():
                raise RuntimeError(f"Missing verified {stage} checkpoint transfer")
            _restore_one(stage, checkpoint_dir, import_dir)
        if stage == "finish":
            _restore_finish_manifest(checkpoint_dir, import_dir)
        restored.append(stage)
    return tuple(restored)


def _required_prior_stages(target: str) -> tuple[str, ...]:
    if target == "generate":
        return ()
    if target == "augment":
        return ("generate",)
    if target == "train":
        return ("generate", "augment")
    if target == "finish":
        return TRAINING_STAGES
    raise ValueError(f"Unknown browser checkpoint target: {target}")


def run_target(
    target: str,
    workspace: Path,
    checkpoint_dir: Path,
    import_dir: Path,
    transfer_dir: Path,
) -> tuple[Path, ...]:
    if target not in STAGES:
        raise ValueError(f"Unknown browser checkpoint target: {target}")
    required = _required_prior_stages(target)
    if required:
        try:
            restore_through(required[-1], checkpoint_dir, import_dir)
        except RuntimeError as error:
            missing = required[-1]
            raise RuntimeError(
                f"Target {target} requires a verified {missing} checkpoint before prepare"
            ) from error

    TRAINER.require_host_runtime()
    TRAINER.prepare(workspace, checkpoint_dir, TRAINER.DEFAULT_CONFIG)
    if target == "finish":
        for stage in TRAINING_STAGES:
            TRAINER.run_training_stage(workspace, checkpoint_dir, stage)
        TRAINER.convert(workspace, checkpoint_dir)
        TRAINER.verify_candidate(workspace)
        TRAINER.bundle(workspace, checkpoint_dir)
    else:
        for stage in TRAINING_STAGES[: TRAINING_STAGES.index(target) + 1]:
            TRAINER.run_training_stage(workspace, checkpoint_dir, stage)
    return pack_checkpoint(target, checkpoint_dir, transfer_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack", help="Split one verified checkpoint for browser transfer")
    pack.add_argument("--stage", choices=tuple(STAGES), required=True)
    restore = commands.add_parser("restore", help="Restore cumulative browser checkpoint parts")
    restore.add_argument("--through", choices=tuple(STAGES), required=True)
    run = commands.add_parser("run", help="Run through one durable training boundary")
    run.add_argument("--target", choices=tuple(STAGES), required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    require_local_boundaries(WORKSPACE, CHECKPOINT_DIR, IMPORT_DIR, TRANSFER_DIR)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    TRANSFER_DIR.mkdir(parents=True, exist_ok=True)
    if args.command == "pack":
        outputs = pack_checkpoint(args.stage, CHECKPOINT_DIR, TRANSFER_DIR)
    elif args.command == "restore":
        restore_through(args.through, CHECKPOINT_DIR, IMPORT_DIR)
        outputs = ()
    else:
        outputs = run_target(args.target, WORKSPACE, CHECKPOINT_DIR, IMPORT_DIR, TRANSFER_DIR)
    print(json.dumps(provenance(), indent=2, sort_keys=True))
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
