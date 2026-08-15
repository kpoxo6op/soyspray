#!/usr/bin/env python3
"""Render the canonical synthetic-only GI V4 plan with pinned Piper code."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import shutil
import sys
import wave
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType

DRIVER = Path(__file__).resolve()
PLAN_HELPER = DRIVER.with_name("gi_v4_synthesis_plan.py")
PLAN_FILENAME = "gi-v4-synthesis-plan.json"
MANIFEST_FILENAME = "gi-v4-generated-manifest.json"
PLANNED_NOISE_INTERFACE = 1
PIPER_CONFIG_SHA256 = "119118e510d0b8a7a0c8649a0668640d6db9b00239e874169d964853a8d15848"
SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2
CHANNELS = 1
OUTPUT_DIRS = {
    ("train", "positive"): Path("gi/positive_train"),
    ("train", "negative"): Path("gi/negative_train"),
    ("val", "positive"): Path("gi/positive_test"),
    ("val", "negative"): Path("gi/negative_test"),
}
_PARTITION_ORDER = {"train": 0, "val": 1}
_CLASS_ORDER = {"positive": 0, "negative": 1}
_LOAD_ARGUMENTS = {"model_path", "config_path"}
_BATCH_ARGUMENTS = {
    "renderer",
    "texts",
    "speaker_pairs",
    "slerp_weight",
    "length_scale",
    "noise_scale",
    "noise_scale_w",
    "duration_noise_seeds",
    "latent_noise_seeds",
}


def _sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Missing or unsafe pinned Piper {label}: {path}")


def _verify_hash(path: Path, expected: str, label: str) -> None:
    _require_file(path, label)
    actual = _sha256(path)
    if actual != expected:
        raise RuntimeError(
            f"Unexpected pinned Piper {label} SHA-256: {actual}, expected {expected}"
        )


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Python module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_plan_api() -> ModuleType:
    _require_file(PLAN_HELPER, "GI V4 synthesis plan helper")
    return _load_module(PLAN_HELPER, "gi_v4_synthesis_plan")


def _load_generator(path: Path, expected_sha256: str) -> ModuleType:
    _verify_hash(path, expected_sha256, "generator")
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return _load_module(path, f"gi_v4_piper_{expected_sha256[:12]}")


def _require_keyword_arguments(function: object, names: set[str], label: str) -> None:
    if not callable(function):
        raise RuntimeError(f"Pinned Piper planned-noise interface lacks {label}")
    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"Cannot inspect pinned Piper {label}") from error
    missing = sorted(names - set(parameters))
    positional_only = sorted(
        name
        for name in names & set(parameters)
        if parameters[name].kind is inspect.Parameter.POSITIONAL_ONLY
    )
    if missing or positional_only:
        detail = ", ".join(missing + positional_only)
        raise RuntimeError(f"Pinned Piper {label} does not accept required arguments: {detail}")


def require_planned_noise_interface(generator: object) -> None:
    """Require the explicit per-record duration and latent-noise API."""
    message = (
        "Pinned Piper generator lacks planned-noise interface 1 with "
        "duration_noise_seeds and latent_noise_seeds"
    )
    if getattr(generator, "PLANNED_NOISE_INTERFACE", None) != PLANNED_NOISE_INTERFACE:
        raise RuntimeError(message)
    try:
        _require_keyword_arguments(
            generator.load_planned_model, _LOAD_ARGUMENTS, "load_planned_model"
        )
        _require_keyword_arguments(
            generator.generate_planned_batch,
            _BATCH_ARGUMENTS,
            "generate_planned_batch",
        )
    except (AttributeError, RuntimeError) as error:
        raise RuntimeError(message) from error


def derive_noise_seed(seed: int, domain: str) -> int:
    """Derive one independent signed-63-bit Torch seed from a plan seed."""
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError(f"Invalid GI V4 record seed: {seed!r}")
    if domain not in {"duration", "latent"}:
        raise ValueError(f"Unknown GI V4 noise domain: {domain}")
    payload = b"gi-v4\0" + domain.encode("ascii") + b"\0" + seed.to_bytes(8, "big")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


def _clear_path(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _atomic_bytes(path: Path, data: bytes) -> None:
    part = path.with_name(f"{path.name}.part")
    _clear_path(part)
    with part.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(part, path)


def _write_wav(path: Path, pcm: object) -> None:
    if type(pcm) is not bytes or not pcm or len(pcm) % SAMPLE_WIDTH:
        raise RuntimeError("Pinned Piper returned invalid mono PCM16 frame bytes")
    part = path.with_name(f"{path.name}.part")
    _clear_path(part)
    with part.open("xb") as output:
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm)
        output.flush()
        os.fsync(output.fileno())
    os.replace(part, path)


def _verify_wav(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Missing or unsafe generated WAV: {path}")
    try:
        with wave.open(str(path), "rb") as wav_file:
            actual = (
                wav_file.getnchannels(),
                wav_file.getsampwidth(),
                wav_file.getframerate(),
                wav_file.getcomptype(),
                wav_file.getnframes(),
            )
    except (EOFError, wave.Error) as error:
        raise RuntimeError(f"Invalid generated WAV: {path}") from error
    if actual[:4] != (CHANNELS, SAMPLE_WIDTH, SAMPLE_RATE, "NONE") or actual[4] <= 0:
        raise RuntimeError(f"Unexpected generated WAV format: {path}: {actual}")


def _record_path(record: Mapping[str, object]) -> Path:
    try:
        output_dir = OUTPUT_DIRS[(record["partition"], record["class"])]
        filename = record["filename"]
        index = record["index"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(f"Invalid GI V4 synthesis record: {record!r}") from error
    if (
        type(index) is not int
        or type(filename) is not str
        or filename != f"{index:08d}.wav"
        or Path(filename).name != filename
    ):
        raise RuntimeError(f"Unsafe GI V4 output filename: {filename!r}")
    return output_dir / filename


def _group_key(record: Mapping[str, object]) -> tuple[object, ...]:
    return (
        record["partition"],
        record["class"],
        record["slerp_weight"],
        record["length_scale"],
        record["noise_scale"],
        record["noise_scale_w"],
    )


def _ordered_groups(records: Sequence[Mapping[str, object]]) -> list[list[Mapping[str, object]]]:
    groups: dict[tuple[object, ...], list[Mapping[str, object]]] = {}
    for record in records:
        groups.setdefault(_group_key(record), []).append(record)

    def order(key: tuple[object, ...]) -> tuple[object, ...]:
        return (
            _PARTITION_ORDER.get(key[0], 99),
            _CLASS_ORDER.get(key[1], 99),
            *key[2:],
        )

    return [groups[key] for key in sorted(groups, key=order)]


def _piper_provenance(
    plan: Mapping[str, object],
    model: Path,
    config: Path,
    generator: Path,
    generator_sha256: str,
    config_sha256: str,
) -> dict[str, object]:
    piper = plan.get("piper")
    if type(piper) is not dict:
        raise RuntimeError("GI V4 plan lacks pinned Piper metadata")
    checkpoint_sha256 = piper.get("checkpoint_sha256")
    checkpoint_filename = piper.get("checkpoint_filename")
    if type(checkpoint_sha256) is not str or checkpoint_filename != model.name:
        raise RuntimeError("GI V4 plan does not match the pinned Piper checkpoint")
    _verify_hash(model, checkpoint_sha256, "checkpoint")
    _verify_hash(config, config_sha256, "config")
    _verify_hash(generator, generator_sha256, "generator")
    return {
        "checkpoint_filename": model.name,
        "checkpoint_sha256": checkpoint_sha256,
        "config_filename": config.name,
        "config_sha256": config_sha256,
        "generator_filename": generator.name,
        "generator_sha256": generator_sha256,
        "planned_noise_interface": PLANNED_NOISE_INTERFACE,
    }


def _expected_manifest(
    plan: Mapping[str, object],
    root: Path,
    piper: Mapping[str, object],
    plan_bytes: bytes,
) -> dict[str, object]:
    records = plan.get("records")
    if type(records) is not list:
        raise RuntimeError("GI V4 plan records must be a list")
    expected_paths: set[Path] = set()
    generated: list[dict[str, object]] = []
    counts = {path.name: 0 for path in OUTPUT_DIRS.values()}
    for record in records:
        if type(record) is not dict:
            raise RuntimeError("GI V4 plan has a non-object record")
        if {"file", "bytes", "sha256"} & set(record):
            raise RuntimeError("GI V4 plan record contains generated fields")
        relative = _record_path(record)
        if relative in expected_paths:
            raise RuntimeError(f"Duplicate GI V4 output path: {relative}")
        expected_paths.add(relative)
        path = root / relative
        _verify_wav(path)
        counts[relative.parent.name] += 1
        generated.append(
            {
                **record,
                "file": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )

    actual_paths: set[Path] = set()
    gi_root = root / "gi"
    if gi_root.is_symlink() or not gi_root.is_dir():
        raise RuntimeError(f"Missing or unsafe GI V4 audio root: {gi_root}")
    expected_directories = set(OUTPUT_DIRS.values()) | {Path("gi")}
    actual_directories = {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_dir() and not path.is_symlink()
    }
    if actual_directories != expected_directories:
        raise RuntimeError("GI V4 generated directory set does not match the plan")
    for path in gi_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Unsafe generated path: {path}")
        if path.is_file():
            actual_paths.add(path.relative_to(root))
    if actual_paths != expected_paths:
        raise RuntimeError("GI V4 generated WAV set does not match the plan")

    return {
        "schema_version": 1,
        "human_audio_used": False,
        "plan_sha256": _sha256_bytes(plan_bytes),
        "piper": dict(piper),
        "sample_format": {
            "channels": CHANNELS,
            "sample_rate": SAMPLE_RATE,
            "sample_width_bytes": SAMPLE_WIDTH,
        },
        "counts": counts,
        "records": generated,
    }


def verify_generated_stage(
    plan: object,
    root: Path,
    expected_piper: object,
    *,
    _plan_api: object | None = None,
) -> dict[str, object]:
    """Fail closed unless a generated stage exactly matches its canonical plan."""
    plan_api = _plan_api or _load_plan_api()
    plan_api.verify_plan(plan)
    if type(plan) is not dict or plan.get("human_audio_used") is not False:
        raise RuntimeError("GI V4 generation accepts only a synthetic plan")
    if type(expected_piper) is not dict:
        raise RuntimeError("Invalid expected Piper provenance")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"Missing or unsafe GI V4 generated stage: {root}")
    plan_bytes = plan_api.canonical_json(plan)
    saved_plan = root / PLAN_FILENAME
    _require_file(saved_plan, "GI V4 saved synthesis plan")
    if saved_plan.read_bytes() != plan_bytes:
        raise RuntimeError("Saved GI V4 synthesis plan does not match the canonical plan")
    manifest_path = root / MANIFEST_FILENAME
    _require_file(manifest_path, "GI V4 generated manifest")
    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError("Invalid GI V4 generated manifest JSON") from error
    expected = _expected_manifest(plan, root, expected_piper, plan_bytes)
    if manifest != expected:
        raise RuntimeError("GI V4 generated manifest does not match the plan and WAV hashes")
    expected_files = {
        Path(PLAN_FILENAME),
        Path(MANIFEST_FILENAME),
        *(_record_path(record) for record in plan["records"]),
    }
    actual_files = {
        path.relative_to(root) for path in root.rglob("*") if path.is_file() or path.is_symlink()
    }
    if actual_files != expected_files:
        raise RuntimeError("GI V4 generated stage contains unexpected files")
    return manifest


def render_stage(
    plan: object,
    output_root: Path,
    model_path: Path,
    generator_path: Path,
    *,
    expected_generator_sha256: str,
    batch_size: int = 32,
    _plan_api: object | None = None,
    _generator_module: object | None = None,
    _expected_config_sha256: str = PIPER_CONFIG_SHA256,
) -> dict[str, object]:
    """Render a verified plan in a new tree, verify it, then promote it."""
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    plan_api = _plan_api or _load_plan_api()
    plan_api.verify_plan(plan)
    if type(plan) is not dict or plan.get("human_audio_used") is not False:
        raise RuntimeError("GI V4 generation accepts only a synthetic plan")
    output_root = Path(output_root)
    if output_root.parent == output_root or not output_root.name:
        raise ValueError(f"Unsafe GI V4 output root: {output_root}")
    if output_root.exists() or output_root.is_symlink():
        raise RuntimeError(f"GI V4 output root already exists: {output_root}")
    model_path = Path(model_path)
    generator_path = Path(generator_path)
    config_path = Path(f"{model_path}.json")
    generator = _generator_module or _load_generator(generator_path, expected_generator_sha256)
    require_planned_noise_interface(generator)
    piper = _piper_provenance(
        plan,
        model_path,
        config_path,
        generator_path,
        expected_generator_sha256,
        _expected_config_sha256,
    )

    part_root = output_root.with_name(f"{output_root.name}.part")
    _clear_path(part_root)
    renderer = generator.load_planned_model(model_path=model_path, config_path=config_path)
    part_root.mkdir(parents=True)
    for relative in OUTPUT_DIRS.values():
        (part_root / relative).mkdir(parents=True)
    plan_bytes = plan_api.canonical_json(plan)
    _atomic_bytes(part_root / PLAN_FILENAME, plan_bytes)

    records = plan.get("records")
    if type(records) is not list:
        raise RuntimeError("GI V4 plan records must be a list")
    for group in _ordered_groups(records):
        for start in range(0, len(group), batch_size):
            batch = group[start : start + batch_size]
            key = _group_key(batch[0])
            pcm_frames = generator.generate_planned_batch(
                renderer,
                texts=[record["text"] for record in batch],
                speaker_pairs=[tuple(record["speakers"]) for record in batch],
                slerp_weight=key[2],
                length_scale=key[3],
                noise_scale=key[4],
                noise_scale_w=key[5],
                duration_noise_seeds=[
                    derive_noise_seed(record["seed"], "duration") for record in batch
                ],
                latent_noise_seeds=[
                    derive_noise_seed(record["seed"], "latent") for record in batch
                ],
            )
            if type(pcm_frames) is not list or len(pcm_frames) != len(batch):
                raise RuntimeError("Pinned Piper returned the wrong planned batch size")
            for record, pcm in zip(batch, pcm_frames, strict=True):
                _write_wav(part_root / _record_path(record), pcm)

    manifest = _expected_manifest(plan, part_root, piper, plan_bytes)
    _atomic_bytes(
        part_root / MANIFEST_FILENAME,
        (json.dumps(manifest, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(),
    )
    verify_generated_stage(plan, part_root, piper, _plan_api=plan_api)
    os.replace(part_root, output_root)
    return verify_generated_stage(plan, output_root, piper, _plan_api=plan_api)


def _load_json(path: Path) -> object:
    _require_file(path, "GI V4 synthesis plan")
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"Invalid GI V4 synthesis plan JSON: {path}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--generator-sha256", required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    manifest = render_stage(
        _load_json(args.plan),
        args.output_root,
        args.model,
        args.generator,
        expected_generator_sha256=args.generator_sha256,
        batch_size=args.batch_size,
    )
    print(
        json.dumps(
            {
                "manifest": str(args.output_root / MANIFEST_FILENAME),
                "records": len(manifest["records"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
