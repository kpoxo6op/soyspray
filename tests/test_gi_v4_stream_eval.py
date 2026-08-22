from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import struct
import wave
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gi_v4_stream_eval.py"


def _load_module() -> ModuleType:
    assert SCRIPT.is_file(), "missing GI v4 streaming evaluator"
    spec = importlib.util.spec_from_file_location("gi_v4_stream_eval", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module() -> ModuleType:
    return _load_module()


def _write_wav(
    path: Path,
    *,
    samples: int = 80,
    sample_rate: int = 16_000,
    channels: int = 1,
    sample_width: int = 2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x01\x00" * samples * channels)


def _write_npy(path: Path, *, shape: tuple[int, int], descr: str = "<f4") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dictionary = (
        f"{{'descr': '{descr}', 'fortran_order': False, 'shape': ({shape[0]}, {shape[1]}), }}"
    ).encode("latin1")
    padding = (-((10 + len(dictionary) + 1) % 16)) % 16
    header = dictionary + (b" " * padding) + b"\n"
    prefix = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header))
    path.write_bytes(prefix + header + (b"\x00" * shape[0] * shape[1] * 4))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wav(path: Path, root: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}


def _pin_test_features(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
    *,
    expected_shape: tuple[int, int],
) -> None:
    monkeypatch.setattr(module, "GENERIC_FEATURE_SHAPE", expected_shape)
    monkeypatch.setattr(module, "GENERIC_FEATURE_BYTES", path.stat().st_size)
    monkeypatch.setattr(module, "GENERIC_FEATURE_SHA256", _sha256(path))


def _manifest(
    module: ModuleType,
    input_root: Path,
    feature_path: Path,
    groups: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "human_audio_used": False,
        "generation": {
            "generated_manifest_sha256": "1" * 64,
            "plan_sha256": "2" * 64,
        },
        "generic_negative": {
            "path": feature_path.relative_to(input_root).as_posix(),
            "sha256": _sha256(feature_path),
            "bytes": feature_path.stat().st_size,
            "shape": list(module.GENERIC_FEATURE_SHAPE),
            "dtype": "float32",
            "declared_hours": 11.3,
            "source": "openwakeword_false_positive_validation",
        },
        "groups": groups,
    }


class FakePcmRunner:
    def __init__(self, sequences: list[list[float]]) -> None:
        self.sequences = iter(sequences)
        self.current = iter(())
        self.reset_count = 0
        self.clip_chunks: list[list[bytes]] = []
        self.closed = False

    def reset(self) -> None:
        self.current = iter(next(self.sequences))
        self.reset_count += 1
        self.clip_chunks.append([])

    def process(self, chunk: bytes) -> list[float]:
        self.clip_chunks[-1].append(chunk)
        try:
            return [next(self.current)]
        except StopIteration:
            return []

    def close(self) -> None:
        self.closed = True


class FakeGenericRunner:
    def __init__(self, scores: list[float]) -> None:
        self.scores = iter(scores)
        self.reset_count = 0
        self.rows = 0
        self.row_bytes: list[int] = []
        self.closed = False

    def reset(self) -> None:
        self.reset_count += 1
        self.rows = 0

    def process(self, row: memoryview) -> list[float]:
        self.row_bytes.append(row.nbytes)
        self.rows += 1
        if self.rows < 16:
            return []
        try:
            return [next(self.scores)]
        except StopIteration:
            return []

    def close(self) -> None:
        self.closed = True


def _fixture(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    feature_rows: int = 8,
) -> tuple[Path, dict[str, object], Path]:
    input_root = tmp_path / "inputs"
    feature_path = input_root / "validation_set_features.npy"
    _write_npy(feature_path, shape=(feature_rows, 96))
    _pin_test_features(module, monkeypatch, feature_path, expected_shape=(feature_rows, 96))
    files = {}
    for name in ("explicit", "positive"):
        path = input_root / f"{name}.wav"
        _write_wav(path)
        files[name] = path
    groups = [
        {
            "name": "explicit-nabu",
            "label": "explicit_negative",
            "source": "synthetic",
            "files": [_wav(files["explicit"], input_root)],
        },
        {
            "name": "positive-gee-eye",
            "label": "positive",
            "source": "synthetic",
            "files": [_wav(files["positive"], input_root)],
        },
    ]
    model = tmp_path / "gi.tflite"
    model.write_bytes(b"synthetic model fixture")
    return input_root, _manifest(module, input_root, feature_path, groups), model


def _evaluate(
    module: ModuleType,
    manifest: dict[str, object],
    input_root: Path,
    model: Path,
    pcm: FakePcmRunner,
    generic: FakeGenericRunner,
) -> dict[str, object]:
    return module.evaluate_manifest(
        manifest,
        input_root=input_root,
        model_path=model,
        pcm_runner_factory=lambda _: pcm,
        generic_runner_factory=lambda _: generic,
    )


def test_pinned_generic_feature_contract(module: ModuleType) -> None:
    assert module.GENERIC_FEATURE_SHAPE == (481_345, 96)
    assert module.GENERIC_FEATURE_BYTES == 184_836_608
    assert module.GENERIC_FEATURE_SHA256 == (
        "a56a8a0f8e0efb91900acc6de4c0cdf4c564842e8475a7d49b36c039e17a690f"
    )
    assert module.GENERIC_FEATURE_SHAPE[0] - module.MODEL_INPUT_WINDOWS + 1 == 481_330


def test_trigger_level_is_strict_and_cumulative(module: ModuleType) -> None:
    assert module.activation_from_scores([0.66, 0.1, 0.66]) == (2, True)
    assert module.activation_from_scores([0.65, 0.9]) == (1, False)
    assert module.generic_activations_from_scores([0.66, 0.1, 0.66]) == (2, 1)
    assert module.generic_activations_from_scores([0.65, 0.9]) == (1, 0)


def test_generic_refractory_makes_tick_25_eligible_without_resetting_trigger(
    module: ModuleType,
) -> None:
    scores = [0.66, 0.66] + ([0.9] * 24) + [0.66]
    assert module.generic_activations_from_scores(scores) == (27, 2)
    assert module.generic_activations_from_scores(scores[:-1]) == (26, 1)


def test_wav_clips_reset_and_stream_exact_tail_while_features_do_not_reset(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    pcm = FakePcmRunner([[0.1], [0.66, 0.1, 0.66]])
    generic = FakeGenericRunner([0.1] * 8)

    report = _evaluate(module, manifest, input_root, model, pcm, generic)

    assert pcm.reset_count == 2
    assert generic.reset_count == 1
    assert pcm.closed is generic.closed is True
    for chunks in pcm.clip_chunks:
        stream = b"".join(chunks)
        assert len(stream) // 2 == 80 + 16_000
        assert stream[-32_000:] == b"\x00" * 32_000
        assert all(len(chunk) <= 2 * 1_280 for chunk in chunks)
        assert all(len(chunk) == 2 * 1_280 for chunk in chunks[:-1])
    assert generic.row_bytes == [96 * 4] * 8
    assert report["confusion"] == {
        "true_positive": 1,
        "false_negative": 0,
        "false_positive": 0,
        "true_negative": 1,
    }
    assert report["passed"] is True


def test_group_gates_and_generic_false_positives_per_declared_hour(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path, feature_rows=68)
    pcm = FakePcmRunner([[0.66, 0.66], [0.66, 0.66]])
    generic_scores = [0.66, 0.1, 0.66] + ([0.1] * 24) + [0.66] + ([0.1] * 24) + [0.66]
    generic = FakeGenericRunner(generic_scores)

    report = _evaluate(module, manifest, input_root, model, pcm, generic)

    groups = {group["name"]: group for group in report["groups"]}
    assert groups["positive-gee-eye"]["recall"] == 1.0
    assert groups["explicit-nabu"]["counts"]["activations"] == 1
    assert report["generic_negative"] == {
        "rows": 68,
        "model_outputs": 53,
        "declared_hours": 11.3,
        "crossings": 4,
        "activations": 3,
        "crossings_per_hour": 4 / 11.3,
        "activations_per_hour": 3 / 11.3,
    }
    assert report["gates"] == {
        "minimum_positive_group_recall": 0.95,
        "maximum_explicit_negative_activations": 0,
        "maximum_generic_negative_activations_per_hour": 0.2,
        "positive_groups_passed": True,
        "explicit_negative_passed": False,
        "generic_negative_passed": False,
    }
    assert report["passed"] is False


def test_positive_gate_is_applied_to_each_group(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    positive = manifest["groups"][1]
    files = []
    for index in range(20):
        path = input_root / f"positive-{index:02d}.wav"
        _write_wav(path)
        files.append(_wav(path, input_root))
    positive["files"] = files
    pcm = FakePcmRunner([[0.1]] + ([[0.66, 0.66]] * 19) + [[0.1]])
    generic = FakeGenericRunner([0.1] * 8)

    report = _evaluate(module, manifest, input_root, model, pcm, generic)

    positive_result = report["groups"][1]
    assert positive_result["counts"]["clips"] == 20
    assert positive_result["counts"]["activations"] == 19
    assert positive_result["recall"] == 0.95
    assert report["passed"] is True


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda value: value.update(human_audio_used=True), "human"),
        (lambda value: value["groups"][0].update(source="human"), "synthetic"),
        (lambda value: value["groups"][0].update(label="generic_negative"), "label"),
        (lambda value: value["groups"].reverse(), "sorted"),
        (
            lambda value: value["groups"][0]["files"][0].update(path="../outside.wav"),
            "relative",
        ),
        (
            lambda value: value["generic_negative"].update(source="human_recording"),
            "source",
        ),
        (
            lambda value: value["generation"].update(plan_sha256="not-a-hash"),
            "generation",
        ),
    ],
)
def test_manifest_rejects_human_unordered_or_invalid_inputs(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
    error: str,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    mutation(manifest)

    with pytest.raises((TypeError, ValueError), match=error):
        _evaluate(
            module,
            manifest,
            input_root,
            model,
            FakePcmRunner([]),
            FakeGenericRunner([]),
        )


@pytest.mark.parametrize(
    "fault", ["hash", "file_hash", "bytes", "shape", "dtype", "header_shape", "header_dtype"]
)
def test_generic_npy_fails_closed(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fault: str,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    record = manifest["generic_negative"]
    feature_path = input_root / record["path"]
    if fault == "hash":
        record["sha256"] = "0" * 64
    elif fault == "file_hash":
        with feature_path.open("r+b") as stream:
            stream.seek(-1, 2)
            stream.write(b"\x01")
    elif fault == "bytes":
        record["bytes"] += 1
    elif fault == "shape":
        record["shape"] = [7, 96]
    elif fault == "dtype":
        record["dtype"] = "float64"
    elif fault == "header_shape":
        _write_npy(feature_path, shape=(7, 96))
        monkeypatch.setattr(module, "GENERIC_FEATURE_BYTES", feature_path.stat().st_size)
        monkeypatch.setattr(module, "GENERIC_FEATURE_SHA256", _sha256(feature_path))
        record["bytes"] = feature_path.stat().st_size
        record["sha256"] = _sha256(feature_path)
    else:
        _write_npy(feature_path, shape=(8, 96), descr=">f4")
        monkeypatch.setattr(module, "GENERIC_FEATURE_BYTES", feature_path.stat().st_size)
        monkeypatch.setattr(module, "GENERIC_FEATURE_SHA256", _sha256(feature_path))
        record["bytes"] = feature_path.stat().st_size
        record["sha256"] = _sha256(feature_path)

    with pytest.raises(ValueError, match="generic|NPY|SHA|shape|dtype|bytes"):
        _evaluate(
            module,
            manifest,
            input_root,
            model,
            FakePcmRunner([]),
            FakeGenericRunner([]),
        )


def test_generic_npy_symlink_is_rejected(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    target = input_root / "validation_set_features.npy"
    link = input_root / "linked.npy"
    link.symlink_to(target.name)
    manifest["generic_negative"]["path"] = "linked.npy"

    with pytest.raises(ValueError, match="symlink"):
        _evaluate(
            module,
            manifest,
            input_root,
            model,
            FakePcmRunner([]),
            FakeGenericRunner([]),
        )


def test_wav_symlink_and_wrong_format_are_rejected(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    target = input_root / "explicit.wav"
    link = input_root / "linked.wav"
    link.symlink_to(target.name)
    manifest["groups"][0]["files"] = [{"path": "linked.wav", "sha256": _sha256(target)}]
    with pytest.raises(ValueError, match="symlink"):
        _evaluate(
            module,
            manifest,
            input_root,
            model,
            FakePcmRunner([]),
            FakeGenericRunner([]),
        )

    bad = input_root / "stereo.wav"
    _write_wav(bad, channels=2)
    manifest["groups"][0]["files"] = [_wav(bad, input_root)]
    with pytest.raises(ValueError, match="mono"):
        _evaluate(
            module,
            manifest,
            input_root,
            model,
            FakePcmRunner([]),
            FakeGenericRunner([]),
        )


def test_canonical_manifest_and_report_tampering_fail_closed(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_root, manifest, model = _fixture(module, monkeypatch, tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(module.canonical_json(manifest))
    assert module.load_canonical_manifest(manifest_path) == manifest
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    with pytest.raises(ValueError, match="canonical"):
        module.load_canonical_manifest(manifest_path)

    report = _evaluate(
        module,
        manifest,
        input_root,
        model,
        FakePcmRunner([[0.1], [0.66, 0.66]]),
        FakeGenericRunner([0.1] * 8),
    )
    module.verify_report(report)
    assert report["model"]["sha256"] == _sha256(model)
    assert len(report["runtime"]["sha256"]) == 64
    assert report["runtime"] | {"sha256": "ignored"} == {
        "package": "pyopen-wakeword",
        "version": "1.1.0",
        "handler_package": "wyoming-openwakeword",
        "handler_version": "2.1.0",
        "handler_source_sha256": (
            "ec7f2d79b9c9cb3bf426b285b2ef5e6ca1224aee8cbd9e31bc2d5b5a37235a95"
        ),
        "refractory_seconds": 2.0,
        "sha256": "ignored",
    }
    assert report["settings"]["generic_refractory_seconds"] == 2.0
    assert report["settings"]["generic_refractory_ignored_outputs"] == 24
    assert report["settings"]["generic_refractory_eligible_tick"] == 25
    assert report["input"]["generic_feature_sha256"] == _sha256(
        input_root / "validation_set_features.npy"
    )
    assert report["input"]["human_audio_used"] is False
    assert report["input"]["generated_manifest_sha256"] == "1" * 64
    assert report["input"]["plan_sha256"] == "2" * 64

    for mutate in (
        lambda value: value["groups"][1].update(recall=0.5),
        lambda value: value["confusion"].update(true_positive=9),
        lambda value: value["generic_negative"].update(activations=1),
        lambda value: value["model"].update(sha256="0" * 64),
        lambda value: value.update(passed=False),
    ):
        tampered = copy.deepcopy(report)
        mutate(tampered)
        with pytest.raises(ValueError, match="tampered"):
            module.verify_report(tampered)

    resealed = copy.deepcopy(report)
    resealed["groups"][1]["recall"] = 0.5
    payload = {key: value for key, value in resealed.items() if key != "report_sha256"}
    resealed["report_sha256"] = hashlib.sha256(module.canonical_json(payload)).hexdigest()
    with pytest.raises(ValueError, match="recall"):
        module.verify_report(resealed)


def test_invalid_scores_fail_closed(module: ModuleType) -> None:
    for scores in ([float("nan")], [-0.1], [1.1], [True], [[0.7]]):
        with pytest.raises((TypeError, ValueError)):
            module.activation_from_scores(scores)
        with pytest.raises((TypeError, ValueError)):
            module.generic_activations_from_scores(scores)
