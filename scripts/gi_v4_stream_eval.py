#!/usr/bin/env python3
"""Evaluate a frozen GI model with its pinned production-style streams."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import io
import json
import math
import mmap
import os
import re
import struct
import wave
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Iterator, Protocol

SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1
PYOPEN_WAKEWORD_PACKAGE = "pyopen-wakeword"
PYOPEN_WAKEWORD_VERSION = "1.1.0"
WYOMING_OPENWAKEWORD_PACKAGE = "wyoming-openwakeword"
WYOMING_OPENWAKEWORD_VERSION = "2.1.0"
WYOMING_HANDLER_SHA256 = "ec7f2d79b9c9cb3bf426b285b2ef5e6ca1224aee8cbd9e31bc2d5b5a37235a95"

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2
CHUNK_SAMPLES = 1_280
TAIL_ZERO_SAMPLES = 16_000
SCORE_THRESHOLD = 0.65
TRIGGER_LEVEL = 2
MODEL_INPUT_WINDOWS = 16
SCORE_TICK_MILLISECONDS = 80
REFRACTORY_SECONDS = 2.0
REFRACTORY_IGNORED_OUTPUTS = 24
REFRACTORY_ELIGIBLE_TICK = 25

GENERIC_FEATURE_SHAPE = (481_345, 96)
GENERIC_FEATURE_BYTES = 184_836_608
GENERIC_FEATURE_SHA256 = "a56a8a0f8e0efb91900acc6de4c0cdf4c564842e8475a7d49b36c039e17a690f"
GENERIC_FEATURE_DTYPE = "float32"
GENERIC_FEATURE_SOURCE = "openwakeword_false_positive_validation"
GENERIC_FEATURE_HOURS = 11.3

MINIMUM_POSITIVE_RECALL = 0.95
MAXIMUM_EXPLICIT_NEGATIVE_ACTIVATIONS = 0
MAXIMUM_GENERIC_NEGATIVE_ACTIVATIONS_PER_HOUR = 0.2
WAV_LABELS = ("explicit_negative", "positive")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9._/-]*\Z")


class PcmRunner(Protocol):
    def reset(self) -> None: ...

    def process(self, chunk: bytes) -> Iterable[float]: ...

    def close(self) -> None: ...


class GenericRunner(Protocol):
    def reset(self) -> None: ...

    def process(self, row: memoryview) -> Iterable[float]: ...

    def close(self) -> None: ...


def _settings() -> dict[str, Any]:
    return {
        "sample_rate_hz": SAMPLE_RATE,
        "channels": CHANNELS,
        "sample_width_bytes": SAMPLE_WIDTH,
        "chunk_samples": CHUNK_SAMPLES,
        "tail_zero_samples": TAIL_ZERO_SAMPLES,
        "score_operator": ">",
        "score_threshold": SCORE_THRESHOLD,
        "trigger_level": TRIGGER_LEVEL,
        "trigger_counting": "cumulative",
        "reset_each_wav_clip": True,
        "generic_model_input_windows": MODEL_INPUT_WINDOWS,
        "generic_feature_row_period_ms": SCORE_TICK_MILLISECONDS,
        "generic_refractory_seconds": REFRACTORY_SECONDS,
        "generic_refractory_ignored_outputs": REFRACTORY_IGNORED_OUTPUTS,
        "generic_refractory_eligible_tick": REFRACTORY_ELIGIBLE_TICK,
        "generic_reset_once": True,
        "generic_triggers_reset_after_activation": False,
    }


def canonical_json(value: object) -> bytes:
    """Return compact deterministic UTF-8 JSON with one trailing newline."""
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_canonical_manifest(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    try:
        value = json.loads(raw, object_pairs_hook=_object_without_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON manifest: {error}") from error
    if type(value) is not dict:
        raise TypeError("manifest must be a JSON object")
    if canonical_json(value) != raw:
        raise ValueError("manifest must use canonical JSON")
    return value


def _require_exact_keys(value: object, expected: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{name} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{name} keys must be {sorted(expected)}; got {sorted(actual)}")
    return value


def _reject_symlink_components(path: Path, name: str) -> Path:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{name} contains a symlink: {current}")
    return absolute


def _safe_input_path(root: Path, relative: object, suffix: str, name: str) -> tuple[str, Path]:
    if type(relative) is not str or not relative:
        raise TypeError(f"{name} path must be a non-empty string")
    if "\\" in relative:
        raise ValueError(f"{name} path must be a canonical relative POSIX path")
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or str(pure) != relative
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise ValueError(f"{name} path must be a canonical relative POSIX path")
    if pure.suffix.casefold() != suffix:
        raise ValueError(f"{name} path must end in {suffix}")
    candidate = root.joinpath(*pure.parts)
    _reject_symlink_components(candidate, f"{name} path")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as error:
        raise ValueError(f"{name} path is missing or outside the input root: {relative}") from error
    if not candidate.is_file():
        raise ValueError(f"{name} path is not a regular file: {relative}")
    return relative, candidate


def _validate_generic(record: object, root: Path) -> dict[str, Any]:
    generic = _require_exact_keys(
        record,
        {"path", "sha256", "bytes", "shape", "dtype", "declared_hours", "source"},
        "generic_negative",
    )
    relative, path = _safe_input_path(root, generic["path"], ".npy", "generic NPY")
    if generic["sha256"] != GENERIC_FEATURE_SHA256:
        raise ValueError("generic NPY SHA-256 does not match the pinned dataset")
    if type(generic["bytes"]) is not int or generic["bytes"] != GENERIC_FEATURE_BYTES:
        raise ValueError("generic NPY bytes do not match the pinned dataset")
    if generic["shape"] != list(GENERIC_FEATURE_SHAPE):
        raise ValueError("generic NPY shape does not match the pinned dataset")
    if generic["dtype"] != GENERIC_FEATURE_DTYPE:
        raise ValueError("generic NPY dtype must be float32")
    if (
        type(generic["declared_hours"]) is not float
        or generic["declared_hours"] != GENERIC_FEATURE_HOURS
    ):
        raise ValueError("generic NPY declared_hours must be 11.3")
    if generic["source"] != GENERIC_FEATURE_SOURCE:
        raise ValueError("generic NPY source does not match the pinned public dataset")
    if path.stat().st_size != GENERIC_FEATURE_BYTES:
        raise ValueError("generic NPY file bytes do not match its manifest")
    return {
        "path": relative,
        "absolute_path": path,
        "sha256": GENERIC_FEATURE_SHA256,
        "bytes": GENERIC_FEATURE_BYTES,
        "shape": list(GENERIC_FEATURE_SHAPE),
        "dtype": GENERIC_FEATURE_DTYPE,
        "declared_hours": GENERIC_FEATURE_HOURS,
        "source": GENERIC_FEATURE_SOURCE,
    }


def _validate_manifest(
    manifest: object, input_root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    root = _reject_symlink_components(Path(input_root), "input root")
    if not root.is_dir():
        raise ValueError(f"input root is not a directory: {root}")
    top = _require_exact_keys(
        manifest,
        {"schema_version", "human_audio_used", "generation", "generic_negative", "groups"},
        "manifest",
    )
    if type(top["schema_version"]) is not int or top["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"manifest schema_version must be {MANIFEST_SCHEMA_VERSION}")
    if top["human_audio_used"] is not False:
        raise ValueError("manifest must declare human_audio_used false")
    generation = _require_exact_keys(
        top["generation"], {"generated_manifest_sha256", "plan_sha256"}, "generation"
    )
    for name, value in generation.items():
        if type(value) is not str or not SHA256_RE.fullmatch(value):
            raise ValueError(f"generation {name} must be a lowercase SHA-256")
    generic = _validate_generic(top["generic_negative"], root)
    if type(top["groups"]) is not list or not top["groups"]:
        raise ValueError("manifest groups must be a non-empty ordered list")

    groups: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_names: set[str] = set()
    for index, raw_group in enumerate(top["groups"]):
        group = _require_exact_keys(
            raw_group, {"name", "label", "source", "files"}, f"group {index}"
        )
        name, label, source, raw_files = (
            group["name"],
            group["label"],
            group["source"],
            group["files"],
        )
        if type(name) is not str or not NAME_RE.fullmatch(name):
            raise ValueError(f"group {index} name is invalid")
        if name in seen_names:
            raise ValueError(f"duplicate group name: {name}")
        seen_names.add(name)
        if type(label) is not str or label not in WAV_LABELS:
            raise ValueError(f"group {name} has an invalid synthetic WAV label")
        if source != "synthetic":
            raise ValueError(f"group {name} source must be synthetic")
        if type(raw_files) is not list or not raw_files:
            raise ValueError(f"group {name} files must be a non-empty ordered list")
        files: list[dict[str, Any]] = []
        for file_index, raw_file in enumerate(raw_files):
            item = _require_exact_keys(
                raw_file, {"path", "sha256"}, f"group {name} file {file_index}"
            )
            relative, path = _safe_input_path(root, item["path"], ".wav", "WAV")
            expected_hash = item["sha256"]
            if type(expected_hash) is not str or not SHA256_RE.fullmatch(expected_hash):
                raise ValueError(f"group {name} file {relative} has an invalid SHA-256")
            if relative in seen_paths:
                raise ValueError(f"WAV path occurs more than once: {relative}")
            seen_paths.add(relative)
            files.append({"path": relative, "absolute_path": path, "sha256": expected_hash})
        paths = [item["path"] for item in files]
        if paths != sorted(paths):
            raise ValueError(f"group {name} WAV files must be sorted by path")
        groups.append({"name": name, "label": label, "files": files})

    names = [group["name"] for group in groups]
    if names != sorted(names):
        raise ValueError("manifest groups must be sorted by name")
    if {group["label"] for group in groups} != set(WAV_LABELS):
        raise ValueError(f"manifest must contain all synthetic WAV labels: {list(WAV_LABELS)}")
    return groups, generic, dict(generation)


def _read_pcm16_wav(path: Path, expected_hash: str) -> tuple[bytes, int, str]:
    raw = path.read_bytes()
    actual_hash = _sha256_bytes(raw)
    if actual_hash != expected_hash:
        raise ValueError(f"WAV SHA-256 mismatch: {path.name}")
    try:
        with wave.open(io.BytesIO(raw), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            compression = wav.getcomptype()
            samples = wav.getnframes()
            pcm = wav.readframes(samples)
    except (EOFError, wave.Error) as error:
        raise ValueError(f"invalid WAV file: {path.name}: {error}") from error
    if channels != CHANNELS:
        raise ValueError(f"WAV must be mono: {path.name}")
    if sample_width != SAMPLE_WIDTH:
        raise ValueError(f"WAV must be 16-bit PCM: {path.name}")
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"WAV must be 16000 Hz: {path.name}")
    if compression != "NONE":
        raise ValueError(f"WAV must be uncompressed PCM: {path.name}")
    if type(samples) is not int or samples <= 0 or len(pcm) != samples * SAMPLE_WIDTH:
        raise ValueError(f"WAV has an invalid PCM payload: {path.name}")
    return pcm, samples, actual_hash


def _parse_npy_header(mapped: mmap.mmap) -> int:
    if len(mapped) < 10 or mapped[:6] != b"\x93NUMPY" or mapped[6:8] != b"\x01\x00":
        raise ValueError("generic NPY has an unexpected magic or format version")
    header_length = struct.unpack("<H", mapped[8:10])[0]
    data_offset = 10 + header_length
    if data_offset > len(mapped):
        raise ValueError("generic NPY header exceeds the file")
    raw_header = mapped[10:data_offset]
    if not raw_header.endswith(b"\n"):
        raise ValueError("generic NPY header is not newline terminated")
    try:
        header = ast.literal_eval(raw_header.decode("latin1").strip())
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("generic NPY header is invalid") from error
    if type(header) is not dict or set(header) != {"descr", "fortran_order", "shape"}:
        raise ValueError("generic NPY header keys are invalid")
    if header["descr"] != "<f4":
        raise ValueError("generic NPY header dtype must be little-endian float32")
    if header["fortran_order"] is not False:
        raise ValueError("generic NPY must use C row order")
    if header["shape"] != GENERIC_FEATURE_SHAPE:
        raise ValueError("generic NPY header shape does not match the manifest")
    expected_end = data_offset + math.prod(GENERIC_FEATURE_SHAPE) * 4
    if expected_end != len(mapped):
        raise ValueError("generic NPY payload size does not match its header")
    return data_offset


@contextmanager
def _mapped_generic(record: dict[str, Any]) -> Iterator[tuple[mmap.mmap, int]]:
    path = record["absolute_path"]
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if before.st_size != GENERIC_FEATURE_BYTES:
            raise ValueError("generic NPY bytes changed before evaluation")
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        if digest.hexdigest() != GENERIC_FEATURE_SHA256:
            raise ValueError("generic NPY SHA-256 mismatch")
        after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("generic NPY changed while it was hashed")
        mapped = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            yield mapped, _parse_npy_header(mapped)
        finally:
            mapped.close()


def _validated_score(score: object) -> float:
    if type(score) not in (int, float):
        raise TypeError("model scores must be scalar numbers")
    value = float(score)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("model scores must be finite probabilities from 0 to 1")
    return value


def activation_from_scores(scores: Iterable[float]) -> tuple[int, bool]:
    """Apply strict cumulative trigger level 2 until one WAV detection."""
    crossings = 0
    try:
        iterator = iter(scores)
    except TypeError as error:
        raise TypeError("scores must be an ordered iterable") from error
    for score in iterator:
        if _validated_score(score) > SCORE_THRESHOLD:
            crossings += 1
            if crossings >= TRIGGER_LEVEL:
                return crossings, True
    return crossings, False


def _generic_state() -> dict[str, int]:
    return {
        "model_outputs": 0,
        "crossings": 0,
        "activations": 0,
        "triggers_left": TRIGGER_LEVEL,
        "refractory_left": 0,
    }


def _consume_generic_scores(state: dict[str, int], scores: Iterable[float]) -> None:
    try:
        iterator = iter(scores)
    except TypeError as error:
        raise TypeError("generic scores must be an ordered iterable") from error
    for score in iterator:
        value = _validated_score(score)
        state["model_outputs"] += 1
        crossed = value > SCORE_THRESHOLD
        if crossed:
            state["crossings"] += 1
        if state["refractory_left"] > 0:
            state["refractory_left"] -= 1
            continue
        if crossed:
            if state["triggers_left"] > 0:
                state["triggers_left"] -= 1
            if state["triggers_left"] == 0:
                state["activations"] += 1
                state["refractory_left"] = REFRACTORY_IGNORED_OUTPUTS


def generic_activations_from_scores(scores: Iterable[float]) -> tuple[int, int]:
    """Return raw crossings and handler activations for one ordered score stream."""
    state = _generic_state()
    _consume_generic_scores(state, scores)
    return state["crossings"], state["activations"]


def _stream_chunks(pcm: bytes) -> Iterable[bytes]:
    audio = pcm + (b"\x00" * TAIL_ZERO_SAMPLES * SAMPLE_WIDTH)
    chunk_bytes = CHUNK_SAMPLES * SAMPLE_WIDTH
    for offset in range(0, len(audio), chunk_bytes):
        yield audio[offset : offset + chunk_bytes]


def _require_runtime_version() -> None:
    actual = importlib.metadata.version(PYOPEN_WAKEWORD_PACKAGE)
    if actual != PYOPEN_WAKEWORD_VERSION:
        raise RuntimeError(
            f"{PYOPEN_WAKEWORD_PACKAGE} must be {PYOPEN_WAKEWORD_VERSION}; got {actual}"
        )


class PinnedPcmRunner:
    def __init__(self, model_path: Path) -> None:
        _require_runtime_version()
        from pyopen_wakeword import OpenWakeWord, OpenWakeWordFeatures

        self.features = OpenWakeWordFeatures.from_builtin()
        self.model = OpenWakeWord.from_model(model_path)
        if self.model.input_windows != MODEL_INPUT_WINDOWS:
            raise RuntimeError("wake model must use 16 embedding windows")

    def reset(self) -> None:
        self.features.reset()
        self.model.reset()

    def process(self, chunk: bytes) -> Iterable[float]:
        for embeddings in self.features.process_streaming(chunk):
            yield from self.model.process_streaming(embeddings)

    def close(self) -> None:
        self.model.close()
        self.features.close()


class PinnedGenericRunner:
    def __init__(self, model_path: Path) -> None:
        _require_runtime_version()
        import numpy as np
        from pyopen_wakeword import OpenWakeWord

        self.np = np
        self.model = OpenWakeWord.from_model(model_path)
        if self.model.input_windows != MODEL_INPUT_WINDOWS:
            raise RuntimeError("wake model must use 16 embedding windows")

    def reset(self) -> None:
        self.model.reset()

    def process(self, row: memoryview) -> Iterable[float]:
        embedding = self.np.frombuffer(row, dtype="<f4", count=GENERIC_FEATURE_SHAPE[1])
        embedding = embedding.reshape((1, 1, 1, GENERIC_FEATURE_SHAPE[1]))
        yield from self.model.process_streaming(embedding)

    def close(self) -> None:
        self.model.close()


def _evaluate_pcm(runner: PcmRunner, pcm: bytes) -> tuple[int, bool]:
    runner.reset()
    crossings = 0
    activated = False
    for chunk in _stream_chunks(pcm):
        scores = runner.process(chunk)
        if scores is None:
            raise TypeError("PCM runner must return an ordered score iterable")
        for score in scores:
            value = _validated_score(score)
            if not activated and value > SCORE_THRESHOLD:
                crossings += 1
                if crossings >= TRIGGER_LEVEL:
                    activated = True
    return crossings, activated


def _evaluate_generic(runner: GenericRunner, mapped: mmap.mmap, data_offset: int) -> dict[str, int]:
    runner.reset()
    state = _generic_state()
    row_bytes = GENERIC_FEATURE_SHAPE[1] * 4
    for index in range(GENERIC_FEATURE_SHAPE[0]):
        start = data_offset + index * row_bytes
        row = memoryview(mapped)[start : start + row_bytes]
        try:
            scores = runner.process(row)
            if scores is None:
                raise TypeError("generic runner must return an ordered score iterable")
            _consume_generic_scores(state, scores)
        finally:
            row.release()
    expected_outputs = max(0, GENERIC_FEATURE_SHAPE[0] - MODEL_INPUT_WINDOWS + 1)
    if state["model_outputs"] != expected_outputs:
        raise RuntimeError(
            f"generic runtime produced {state['model_outputs']} outputs; expected {expected_outputs}"
        )
    return state


def _model_record(model_path: Path) -> dict[str, Any]:
    model = _reject_symlink_components(Path(model_path), "model path")
    if model.suffix.casefold() != ".tflite" or not model.is_file():
        raise ValueError("model must be a regular .tflite file without symlinks")
    return {"filename": model.name, "bytes": model.stat().st_size, "sha256": _sha256_file(model)}


def _runtime_record() -> dict[str, Any]:
    identity = {
        "package": PYOPEN_WAKEWORD_PACKAGE,
        "version": PYOPEN_WAKEWORD_VERSION,
        "handler_package": WYOMING_OPENWAKEWORD_PACKAGE,
        "handler_version": WYOMING_OPENWAKEWORD_VERSION,
        "handler_source_sha256": WYOMING_HANDLER_SHA256,
        "refractory_seconds": REFRACTORY_SECONDS,
    }
    return {**identity, "sha256": _sha256_bytes(canonical_json(identity))}


def _counts(
    label: str, clips: int, samples: int, crossings: int, activations: int
) -> dict[str, int]:
    positive = label == "positive"
    return {
        "clips": clips,
        "samples": samples,
        "crossings": crossings,
        "activations": activations,
        "true_positive": activations if positive else 0,
        "false_negative": clips - activations if positive else 0,
        "false_positive": activations if not positive else 0,
        "true_negative": clips - activations if not positive else 0,
    }


def _seal_report(report: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(report)
    sealed["report_sha256"] = _sha256_bytes(canonical_json(report))
    return sealed


def evaluate_manifest(
    manifest: object,
    *,
    input_root: Path,
    model_path: Path,
    pcm_runner_factory: Callable[[Path], PcmRunner] = PinnedPcmRunner,
    generic_runner_factory: Callable[[Path], GenericRunner] = PinnedGenericRunner,
) -> dict[str, Any]:
    """Evaluate synthetic WAV groups and the pinned public feature stream."""
    model = _model_record(Path(model_path))
    groups, generic_input, generation = _validate_manifest(manifest, Path(input_root))
    pcm_runner: PcmRunner | None = None
    generic_runner: GenericRunner | None = None
    results: list[dict[str, Any]] = []
    corpus: list[dict[str, Any]] = []
    with _mapped_generic(generic_input) as (mapped, data_offset):
        try:
            pcm_runner = pcm_runner_factory(Path(model_path))
            generic_runner = generic_runner_factory(Path(model_path))
            for group in groups:
                activations = crossings = samples = 0
                for item in group["files"]:
                    pcm, actual_samples, actual_hash = _read_pcm16_wav(
                        item["absolute_path"], item["sha256"]
                    )
                    clip_crossings, activated = _evaluate_pcm(pcm_runner, pcm)
                    crossings += clip_crossings
                    activations += int(activated)
                    samples += actual_samples
                    corpus.append(
                        {"path": item["path"], "sha256": actual_hash, "samples": actual_samples}
                    )
                clips = len(group["files"])
                results.append(
                    {
                        "name": group["name"],
                        "label": group["label"],
                        "counts": _counts(group["label"], clips, samples, crossings, activations),
                        "recall": activations / clips if group["label"] == "positive" else None,
                    }
                )
            generic_state = _evaluate_generic(generic_runner, mapped, data_offset)
        finally:
            if generic_runner is not None:
                generic_runner.close()
            if pcm_runner is not None:
                pcm_runner.close()

    confusion = {
        key: sum(group["counts"][key] for group in results)
        for key in ("true_positive", "false_negative", "false_positive", "true_negative")
    }
    generic = {
        "rows": GENERIC_FEATURE_SHAPE[0],
        "model_outputs": generic_state["model_outputs"],
        "declared_hours": GENERIC_FEATURE_HOURS,
        "crossings": generic_state["crossings"],
        "activations": generic_state["activations"],
        "crossings_per_hour": generic_state["crossings"] / GENERIC_FEATURE_HOURS,
        "activations_per_hour": generic_state["activations"] / GENERIC_FEATURE_HOURS,
    }
    explicit_activations = sum(
        group["counts"]["activations"] for group in results if group["label"] == "explicit_negative"
    )
    gates = {
        "minimum_positive_group_recall": MINIMUM_POSITIVE_RECALL,
        "maximum_explicit_negative_activations": MAXIMUM_EXPLICIT_NEGATIVE_ACTIVATIONS,
        "maximum_generic_negative_activations_per_hour": (
            MAXIMUM_GENERIC_NEGATIVE_ACTIVATIONS_PER_HOUR
        ),
        "positive_groups_passed": all(
            group["recall"] >= MINIMUM_POSITIVE_RECALL
            for group in results
            if group["label"] == "positive"
        ),
        "explicit_negative_passed": explicit_activations == 0,
        "generic_negative_passed": (
            generic["activations_per_hour"] <= MAXIMUM_GENERIC_NEGATIVE_ACTIVATIONS_PER_HOUR
        ),
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "model": model,
        "runtime": _runtime_record(),
        "input": {
            "human_audio_used": False,
            "manifest_sha256": _sha256_bytes(canonical_json(manifest)),
            "wav_corpus_sha256": _sha256_bytes(canonical_json(corpus)),
            "wav_files": len(corpus),
            "audio_samples": sum(item["samples"] for item in corpus),
            "generic_feature_sha256": GENERIC_FEATURE_SHA256,
            "generic_feature_bytes": GENERIC_FEATURE_BYTES,
            "generic_feature_shape": list(GENERIC_FEATURE_SHAPE),
            **generation,
        },
        "settings": _settings(),
        "groups": results,
        "confusion": confusion,
        "generic_negative": generic,
        "gates": gates,
        "passed": all(
            (
                gates["positive_groups_passed"],
                gates["explicit_negative_passed"],
                gates["generic_negative_passed"],
            )
        ),
    }
    sealed = _seal_report(report)
    verify_report(sealed)
    return sealed


def _require_nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"report is tampered: {name} must be a non-negative integer")
    return value


def _require_hash(value: object, name: str) -> str:
    if type(value) is not str or not SHA256_RE.fullmatch(value):
        raise ValueError(f"report is tampered: {name} is not a SHA-256")
    return value


def verify_report(report: object) -> None:
    """Recompute every ratio and gate, and reject changed report fields."""
    if type(report) is not dict:
        raise ValueError("report is tampered: root must be an object")
    expected_keys = {
        "schema_version",
        "model",
        "runtime",
        "input",
        "settings",
        "groups",
        "confusion",
        "generic_negative",
        "gates",
        "passed",
        "report_sha256",
    }
    if set(report) != expected_keys:
        raise ValueError("report is tampered: root keys changed")
    seal = _require_hash(report["report_sha256"], "report_sha256")
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    if _sha256_bytes(canonical_json(payload)) != seal:
        raise ValueError("report is tampered: report SHA-256 mismatch")
    if (
        type(report["schema_version"]) is not int
        or report["schema_version"] != SCHEMA_VERSION
        or report["settings"] != _settings()
    ):
        raise ValueError("report is tampered: schema or settings changed")

    model = _require_exact_keys(report["model"], {"filename", "bytes", "sha256"}, "model")
    if type(model["filename"]) is not str or not model["filename"].endswith(".tflite"):
        raise ValueError("report is tampered: model filename changed")
    _require_nonnegative_int(model["bytes"], "model bytes")
    _require_hash(model["sha256"], "model sha256")
    runtime = _require_exact_keys(
        report["runtime"],
        {
            "package",
            "version",
            "handler_package",
            "handler_version",
            "handler_source_sha256",
            "refractory_seconds",
            "sha256",
        },
        "runtime",
    )
    if runtime != _runtime_record():
        raise ValueError("report is tampered: pinned runtime changed")
    input_record = _require_exact_keys(
        report["input"],
        {
            "human_audio_used",
            "manifest_sha256",
            "wav_corpus_sha256",
            "wav_files",
            "audio_samples",
            "generic_feature_sha256",
            "generic_feature_bytes",
            "generic_feature_shape",
            "generated_manifest_sha256",
            "plan_sha256",
        },
        "input",
    )
    _require_hash(input_record["manifest_sha256"], "manifest sha256")
    _require_hash(input_record["wav_corpus_sha256"], "WAV corpus sha256")
    input_files = _require_nonnegative_int(input_record["wav_files"], "input wav_files")
    input_samples = _require_nonnegative_int(input_record["audio_samples"], "input audio_samples")
    if input_record["human_audio_used"] is not False:
        raise ValueError("report is tampered: human audio boundary changed")
    if (
        input_record["generic_feature_sha256"] != GENERIC_FEATURE_SHA256
        or input_record["generic_feature_bytes"] != GENERIC_FEATURE_BYTES
        or input_record["generic_feature_shape"] != list(GENERIC_FEATURE_SHAPE)
    ):
        raise ValueError("report is tampered: generic feature identity changed")
    _require_hash(input_record["generated_manifest_sha256"], "generated manifest sha256")
    _require_hash(input_record["plan_sha256"], "plan sha256")

    if type(report["groups"]) is not list or not report["groups"]:
        raise ValueError("report is tampered: groups changed")
    group_names: list[str] = []
    present_labels: set[str] = set()
    totals = {
        key: 0
        for key in (
            "clips",
            "samples",
            "true_positive",
            "false_negative",
            "false_positive",
            "true_negative",
        )
    }
    explicit_activations = 0
    positive_passed = True
    for index, raw_group in enumerate(report["groups"]):
        group = _require_exact_keys(
            raw_group, {"name", "label", "counts", "recall"}, f"group {index}"
        )
        name, label = group["name"], group["label"]
        if type(name) is not str or not NAME_RE.fullmatch(name) or label not in WAV_LABELS:
            raise ValueError("report is tampered: group identity changed")
        group_names.append(name)
        present_labels.add(label)
        counts = _require_exact_keys(
            group["counts"],
            {
                "clips",
                "samples",
                "crossings",
                "activations",
                "true_positive",
                "false_negative",
                "false_positive",
                "true_negative",
            },
            f"group {name} counts",
        )
        values = {
            key: _require_nonnegative_int(value, f"{name} {key}") for key, value in counts.items()
        }
        clips, activations, crossings = (
            values["clips"],
            values["activations"],
            values["crossings"],
        )
        if (
            clips == 0
            or activations > clips
            or not (2 * activations <= crossings <= clips + activations)
        ):
            raise ValueError("report is tampered: impossible WAV group counts")
        if counts != _counts(label, clips, values["samples"], crossings, activations):
            raise ValueError("report is tampered: WAV confusion counts changed")
        expected_recall = activations / clips if label == "positive" else None
        if group["recall"] != expected_recall:
            raise ValueError("report is tampered: group recall was not recomputed")
        if label == "positive":
            positive_passed = positive_passed and expected_recall >= MINIMUM_POSITIVE_RECALL
        else:
            explicit_activations += activations
        for key in totals:
            totals[key] += values[key]

    if group_names != sorted(set(group_names)) or present_labels != set(WAV_LABELS):
        raise ValueError("report is tampered: groups are unordered, duplicated, or incomplete")
    if input_files != totals["clips"] or input_samples != totals["samples"]:
        raise ValueError("report is tampered: WAV input totals changed")
    expected_confusion = {
        key: totals[key]
        for key in ("true_positive", "false_negative", "false_positive", "true_negative")
    }
    if report["confusion"] != expected_confusion:
        raise ValueError("report is tampered: confusion totals changed")

    generic = _require_exact_keys(
        report["generic_negative"],
        {
            "rows",
            "model_outputs",
            "declared_hours",
            "crossings",
            "activations",
            "crossings_per_hour",
            "activations_per_hour",
        },
        "generic_negative",
    )
    rows = _require_nonnegative_int(generic["rows"], "generic rows")
    outputs = _require_nonnegative_int(generic["model_outputs"], "generic model_outputs")
    crossings = _require_nonnegative_int(generic["crossings"], "generic crossings")
    activations = _require_nonnegative_int(generic["activations"], "generic activations")
    expected_outputs = max(0, rows - MODEL_INPUT_WINDOWS + 1)
    if (
        rows != GENERIC_FEATURE_SHAPE[0]
        or outputs != expected_outputs
        or crossings > outputs
        or activations > crossings
        or (activations > 0 and crossings < activations + 1)
    ):
        raise ValueError("report is tampered: generic counts are impossible")
    expected_generic = {
        "rows": rows,
        "model_outputs": outputs,
        "declared_hours": GENERIC_FEATURE_HOURS,
        "crossings": crossings,
        "activations": activations,
        "crossings_per_hour": crossings / GENERIC_FEATURE_HOURS,
        "activations_per_hour": activations / GENERIC_FEATURE_HOURS,
    }
    if generic != expected_generic:
        raise ValueError("report is tampered: generic ratios changed")
    expected_gates = {
        "minimum_positive_group_recall": MINIMUM_POSITIVE_RECALL,
        "maximum_explicit_negative_activations": MAXIMUM_EXPLICIT_NEGATIVE_ACTIVATIONS,
        "maximum_generic_negative_activations_per_hour": (
            MAXIMUM_GENERIC_NEGATIVE_ACTIVATIONS_PER_HOUR
        ),
        "positive_groups_passed": positive_passed,
        "explicit_negative_passed": explicit_activations == 0,
        "generic_negative_passed": (
            expected_generic["activations_per_hour"]
            <= MAXIMUM_GENERIC_NEGATIVE_ACTIVATIONS_PER_HOUR
        ),
    }
    if report["gates"] != expected_gates:
        raise ValueError("report is tampered: gates were not recomputed")
    expected_passed = all(
        (
            expected_gates["positive_groups_passed"],
            expected_gates["explicit_negative_passed"],
            expected_gates["generic_negative_passed"],
        )
    )
    if type(report["passed"]) is not bool or report["passed"] != expected_passed:
        raise ValueError("report is tampered: passed does not match the gates")


def _atomic_write(path: Path, value: bytes) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{destination}.part")
    if destination.is_symlink() or temporary.is_symlink():
        raise ValueError("refusing a symlink report path")
    temporary.unlink(missing_ok=True)
    with temporary.open("xb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = evaluate_manifest(
        load_canonical_manifest(args.manifest),
        input_root=args.input_root,
        model_path=args.model,
    )
    _atomic_write(args.output, canonical_json(report))
    print(report["report_sha256"])
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
