#!/usr/bin/env python3
"""Build the synthetic-only GI v4 wake-word candidate on free Colab CUDA."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

DRIVER = Path(__file__).resolve()
ROOT = DRIVER.parents[1]
COMMON_DRIVER = DRIVER.with_name("train_gi_v3_colab.py")
PLAN_SCRIPT = DRIVER.with_name("gi_v4_synthesis_plan.py")
SYNTHESIZER = DRIVER.with_name("gi_v4_synthesize.py")
STREAM_EVALUATOR = DRIVER.with_name("gi_v4_stream_eval.py")
PIPER_PATCH = DRIVER.with_name("gi-v4-piper.patch")
TRAIN_PATCH = DRIVER.with_name("gi-v4-train.patch")
PIPER_PATCH_SHA256 = "1bbceb45fd14d69059293f48aff106b114290746fd703d4eacafa203a9f789f3"
TRAIN_PATCH_SHA256 = "8404df13e2c0afbc9acc24ef50659aa3b94bd4318a15870a95e20b1a672252e7"
PIPER_CONFIG_SHA256 = "119118e510d0b8a7a0c8649a0668640d6db9b00239e874169d964853a8d15848"
PIPER_MODELS_SOURCE_SHA256 = "eb88105d8fc762e1b0e74a85d1da38583e428ab92e66bef0bde06a2c9c75fbe6"
PIPER_GENERATOR_PATCHED_SHA256 = "8f2a6e04c1613682fa3b1f494f948bd56fa6373fe7ea65abd7a8fb3838cd94bf"
PIPER_MODELS_PATCHED_SHA256 = "8e8df32f4bba732d4751d0c7b820b08d0f8a09aefaef3b7d99414a7b978e2dd1"
TRAIN_PATCHED_SHA256 = "17a657bbc3edf295b8952a421861b27932be7dd5833ac0d29274ae7c916cc357"
CONFIG_SHA256 = "a5de7be6e3427c6bdf6b035936c088249da074b85b9da7c1010d232928a75b7f"
CONFIG = (
    ROOT
    / "playbooks/argocd/applications/home-automation/voice-assistant/models"
    / "gi-v4-training.yaml"
)
STREAM_INPUT = Path("gi-v4-work/gi-v4-stream-input.json")
STREAM_REPORT = Path("gi-v4-work/gi-v4-stream-report.json")
VALIDATION_FEATURE_SHAPE = [481_345, 96]
VALIDATION_SPEAKER_GROUPS = 5
STREAM_VALIDATION_COUNTS = {"positive": 2_000, "explicit_negative": 2_000}


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load(COMMON_DRIVER, "train_gi_v4_shared_base")
COMMON_PATCH_TRAIN = BASE.patch_train
COMMON_VERIFY_CANDIDATE = BASE.verify_candidate
COMMON_TRAIN_PATCHED_SHA256 = BASE.TRAIN_PATCHED_SHA256
COMMON_TRAINING_METRICS = BASE.TRAINING_METRICS


def _configure_base() -> None:
    candidate = "gi-v4"
    work_dir = Path(f"{candidate}-work")
    model_dir = work_dir / "gi"
    BASE.DRIVER = DRIVER
    BASE.CANDIDATE = candidate
    BASE.MODEL_NAME = "gi"
    BASE.CONFIG_BASENAME = f"{candidate}-training.yaml"
    BASE.WORK_DIR = work_dir
    BASE.MODEL_DIR = model_dir
    BASE.CONVERSION_DIR = Path(f"{candidate}-conversion")
    BASE.ONNX_PATH = work_dir / "gi.onnx"
    BASE.ONNX_DATA_PATH = Path(f"{BASE.ONNX_PATH}.data")
    BASE.TFLITE_PATH = work_dir / f"{candidate}.tflite"
    BASE.TRAINING_METRICS = work_dir / f"{candidate}-training-metrics.json"
    BASE.PARITY_PATH = work_dir / f"{candidate}-parity.json"
    BASE.MANIFEST_BASENAME = f"{candidate}-manifest.json"
    BASE.TRAINING_FREEZE_BASENAME = f"{candidate}-training-freeze.txt"
    BASE.CONVERSION_FREEZE_BASENAME = f"{candidate}-conversion-freeze.txt"
    BASE.DEFAULT_WORKSPACE = Path("/content") / candidate
    BASE.DEFAULT_CONFIG = CONFIG
    BASE.CONFIG_SHA256 = CONFIG_SHA256
    BASE.TRAINING_TARGETS = {
        "minimum_accuracy": 0.95,
        "minimum_recall": 0.95,
        "maximum_false_positives_per_hour": 0.2,
    }
    BASE.VERIFICATION_LIMITS = {
        **BASE.VERIFICATION_LIMITS,
        "streaming": {
            "threshold": 0.65,
            "trigger_level": 2,
            "minimum_positive_group_recall": 0.95,
            "maximum_explicit_negative_activations": 0,
            "maximum_generic_negative_activations_per_hour": 0.2,
        },
    }
    BASE.STAGE_OUTPUTS = {
        "generate": (
            model_dir / "positive_train",
            model_dir / "positive_test",
            model_dir / "negative_train",
            model_dir / "negative_test",
            work_dir / "gi-v4-synthesis-plan.json",
            work_dir / "gi-v4-generated-manifest.json",
        ),
        "augment": (
            model_dir / "positive_features_train.npy",
            model_dir / "positive_features_test.npy",
            model_dir / "negative_features_train.npy",
            model_dir / "negative_features_test.npy",
        ),
        "train": (BASE.ONNX_PATH, BASE.TRAINING_METRICS),
    }
    BASE.GENERATED_COUNTS = {
        model_dir / "positive_train": 20_000,
        model_dir / "positive_test": 2_000,
        model_dir / "negative_train": 20_000,
        model_dir / "negative_test": 2_000,
    }
    BASE.FEATURE_SHAPES = {
        model_dir / "positive_features_train.npy": (20_000, 16, 96),
        model_dir / "positive_features_test.npy": (2_000, 16, 96),
        model_dir / "negative_features_train.npy": (20_000, 16, 96),
        model_dir / "negative_features_test.npy": (2_000, 16, 96),
    }


_configure_base()


def _extra_checkpoint_provenance() -> dict[str, object]:
    return {
        "candidate": BASE.CANDIDATE,
        "common_driver_sha256": BASE.sha256(COMMON_DRIVER),
        "synthesis_plan_sha256": BASE.sha256(PLAN_SCRIPT),
        "synthesizer_sha256": BASE.sha256(SYNTHESIZER),
        "stream_evaluator_sha256": BASE.sha256(STREAM_EVALUATOR),
        "piper_patch_sha256": BASE.sha256(PIPER_PATCH),
        "piper_models_sha256": PIPER_MODELS_PATCHED_SHA256,
        "train_patch_sha256": BASE.sha256(TRAIN_PATCH),
    }


def _generate_operation(workspace: Path, staged_config: Path) -> list[str]:
    del staged_config
    return [
        str(BASE._python(workspace / ".venv-train")),
        str(DRIVER),
        "--internal-generate",
        "--workspace",
        str(workspace),
    ]


def _patch_piper_checkout(source: Path) -> None:
    allowed = {
        Path("generate_samples.py"): BASE.PIPER_SOURCE_SHA256,
        Path("piper_train/vits/models.py"): PIPER_MODELS_SOURCE_SHA256,
    }
    patched = {
        Path("generate_samples.py"): PIPER_GENERATOR_PATCHED_SHA256,
        Path("piper_train/vits/models.py"): PIPER_MODELS_PATCHED_SHA256,
    }
    current = {relative: BASE.sha256(source / relative) for relative in allowed}
    if current == patched:
        return
    if current != allowed:
        raise RuntimeError(f"Unexpected GI v4 Piper source hashes: {current}")
    if BASE.sha256(PIPER_PATCH) != PIPER_PATCH_SHA256:
        raise RuntimeError(f"Unexpected GI v4 Piper patch: {PIPER_PATCH}")
    BASE.run(["git", "apply", "--check", str(PIPER_PATCH)], cwd=source)
    BASE.run(["git", "apply", str(PIPER_PATCH)], cwd=source)
    actual = {relative: BASE.sha256(source / relative) for relative in patched}
    if actual != patched:
        raise RuntimeError(f"Unexpected patched GI v4 Piper hashes: {actual}")


def _patch_train(path: Path) -> None:
    actual = BASE.sha256(path)
    if actual == TRAIN_PATCHED_SHA256:
        return
    if actual == BASE.TRAIN_SOURCE_SHA256:
        configured = BASE.TRAIN_PATCHED_SHA256
        configured_metrics = BASE.TRAINING_METRICS
        BASE.TRAIN_PATCHED_SHA256 = COMMON_TRAIN_PATCHED_SHA256
        BASE.TRAINING_METRICS = COMMON_TRAINING_METRICS
        try:
            COMMON_PATCH_TRAIN(path)
        finally:
            BASE.TRAIN_PATCHED_SHA256 = configured
            BASE.TRAINING_METRICS = configured_metrics
        actual = BASE.sha256(path)
    if actual != COMMON_TRAIN_PATCHED_SHA256:
        raise RuntimeError(f"Unexpected common patched trainer SHA-256: {actual}")
    if BASE.sha256(TRAIN_PATCH) != TRAIN_PATCH_SHA256:
        raise RuntimeError(f"Unexpected GI v4 trainer patch: {TRAIN_PATCH}")
    source = path.parents[1]
    BASE.run(["git", "apply", "--check", str(TRAIN_PATCH)], cwd=source)
    BASE.run(["git", "apply", str(TRAIN_PATCH)], cwd=source)
    actual = BASE.sha256(path)
    if actual != TRAIN_PATCHED_SHA256:
        raise RuntimeError(f"Unexpected patched GI v4 trainer SHA-256: {actual}")


def _piper_allowed_files() -> dict[Path, str]:
    return {
        Path("generate_samples.py"): PIPER_GENERATOR_PATCHED_SHA256,
        Path("piper_train/vits/models.py"): PIPER_MODELS_PATCHED_SHA256,
    }


BASE._extra_checkpoint_provenance = _extra_checkpoint_provenance
BASE._generate_operation = _generate_operation
BASE.patch_train = _patch_train
BASE.patch_piper_checkout = _patch_piper_checkout
BASE._piper_allowed_files = _piper_allowed_files
BASE.PIPER_PATCHED_SHA256 = PIPER_GENERATOR_PATCHED_SHA256
BASE.TRAIN_PATCHED_SHA256 = TRAIN_PATCHED_SHA256


ADVERSARIAL_BUILDER = r"""
import importlib.util
import numpy as np
import pathlib
import sys

plan_path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("gi_v4_synthesis_plan", plan_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {plan_path}")
plan_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan_api)
from openwakeword.data import generate_adversarial_texts

forbidden = {
    "gee eye", "gi", "g i", "g.i.", "gee", "eye", "nabu", "okay nabu",
    "turn on the lights", "turn off the lights",
}

def make(count, seed):
    np.random.seed(seed)
    result = []
    for _ in range(20):
        if len(result) >= count:
            break
        batch = generate_adversarial_texts(
            input_text="gee eye",
            N=max(1000, (count - len(result)) * 2),
            include_partial_phrase=1.0,
            include_input_words=0.2,
        )
        result.extend(
            text for text in batch
            if text.casefold() not in forbidden and "g i" not in text.casefold()
            and "g.i." not in text.casefold()
        )
    if len(result) < count:
        raise RuntimeError(f"Only generated {len(result)} of {count} adversarial texts")
    return result[:count]

plan = plan_api.build_plan(make(10_000, 20260816), make(1_000, 20260817))
sys.stdout.buffer.write(plan_api.canonical_json(plan))
"""


def _build_synthesis_plan(workspace: Path) -> Path:
    environment = os.environ.copy()
    environment["MPLBACKEND"] = "Agg"
    result = subprocess.run(
        [
            str(BASE._python(workspace / ".venv-train")),
            "-c",
            ADVERSARIAL_BUILDER,
            str(PLAN_SCRIPT),
        ],
        cwd=workspace,
        check=True,
        capture_output=True,
        env=environment,
    )
    path = workspace / "gi-v4-synthesis-plan.json"
    BASE.atomic_text(path, result.stdout.decode("utf-8"))
    return path


def _run_internal_generation(workspace: Path) -> None:
    output_root = workspace / BASE.WORK_DIR
    if output_root.is_symlink() or (output_root.exists() and not output_root.is_dir()):
        raise RuntimeError(f"Refusing unsafe GI v4 generation root: {output_root}")
    if output_root.is_dir():
        shutil.rmtree(output_root)
    plan = _build_synthesis_plan(workspace)
    BASE.run(
        [
            str(BASE._python(workspace / ".venv-train")),
            str(SYNTHESIZER),
            "--plan",
            str(plan),
            "--output-root",
            str(output_root),
            "--generator",
            str(workspace / "piper-sample-generator/generate_samples.py"),
            "--model",
            str(
                workspace
                / "piper-sample-generator/models"
                / BASE.DOWNLOADS["piper_checkpoint"].filename
            ),
            "--generator-sha256",
            PIPER_GENERATOR_PATCHED_SHA256,
        ],
        cwd=workspace,
    )
    plan.unlink(missing_ok=True)


def _expected_piper() -> dict[str, object]:
    checkpoint = BASE.DOWNLOADS["piper_checkpoint"].filename
    return {
        "checkpoint_filename": checkpoint,
        "checkpoint_sha256": BASE.DOWNLOADS["piper_checkpoint"].sha256,
        "config_filename": f"{checkpoint}.json",
        "config_sha256": PIPER_CONFIG_SHA256,
        "generator_filename": "generate_samples.py",
        "generator_sha256": PIPER_GENERATOR_PATCHED_SHA256,
        "planned_noise_interface": 1,
    }


def _stream_manifest_from_records(
    records: object,
    validation_speakers: object,
    *,
    generated_manifest_sha256: object,
    plan_sha256: object,
    _expected_counts: dict[str, int] = STREAM_VALIDATION_COUNTS,
) -> dict[str, object]:
    if type(records) is not list or type(validation_speakers) is not list:
        raise RuntimeError("GI v4 stream inputs must be ordered lists")
    if (
        len(validation_speakers) < VALIDATION_SPEAKER_GROUPS
        or any(type(speaker) is not int for speaker in validation_speakers)
        or len(set(validation_speakers)) != len(validation_speakers)
    ):
        raise RuntimeError("GI v4 validation speaker list is invalid")
    for name, digest in (
        ("generated manifest", generated_manifest_sha256),
        ("synthesis plan", plan_sha256),
    ):
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise RuntimeError(f"GI v4 {name} SHA-256 is invalid")
    speaker_index = {speaker: index for index, speaker in enumerate(validation_speakers)}
    fixed_negative_names = {
        "gee": "explicit-gee",
        "eye": "explicit-eye",
        "nabu": "explicit-nabu",
        "okay nabu": "explicit-okay-nabu",
        "turn on the lights": "explicit-turn-on-the-lights",
        "turn off the lights": "explicit-turn-off-the-lights",
    }
    groups: dict[str, dict[str, object]] = {}
    for index, record in enumerate(records):
        if type(record) is not dict:
            raise RuntimeError(f"GI v4 generated record {index} is invalid")
        if record.get("partition") != "val":
            continue
        class_name = record.get("class")
        text = record.get("text")
        source = record.get("source")
        if class_name == "positive":
            spelling = {"gee eye": "gee-eye", "GI": "gi"}.get(text)
            speakers = record.get("speakers")
            if spelling is None or type(speakers) is not list or len(speakers) != 2:
                raise RuntimeError(f"GI v4 positive record {index} is invalid")
            first = speakers[0]
            if first not in speaker_index:
                raise RuntimeError(f"GI v4 record {index} uses a training speaker")
            bucket = speaker_index[first] * VALIDATION_SPEAKER_GROUPS // len(validation_speakers)
            group_name = f"positive-{spelling}-speaker-{bucket:02d}"
            label = "positive"
        elif class_name == "negative":
            if source == "piper_adversarial":
                group_name = "explicit-adversarial"
            elif source == "piper_fixed" and text in fixed_negative_names:
                group_name = fixed_negative_names[text]
            else:
                raise RuntimeError(f"GI v4 negative record {index} is invalid")
            label = "explicit_negative"
        else:
            raise RuntimeError(f"GI v4 validation record {index} has an invalid class")
        relative = record.get("file")
        digest = record.get("sha256")
        if (
            type(relative) is not str
            or not relative.startswith("gi/")
            or type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise RuntimeError(f"GI v4 generated record {index} has invalid file evidence")
        group = groups.setdefault(
            group_name,
            {"name": group_name, "label": label, "source": "synthetic", "files": []},
        )
        group["files"].append({"path": f"{BASE.WORK_DIR}/{relative}", "sha256": digest})

    expected_names = {
        f"positive-{spelling}-speaker-{bucket:02d}"
        for spelling in ("gee-eye", "gi")
        for bucket in range(VALIDATION_SPEAKER_GROUPS)
    } | {*fixed_negative_names.values(), "explicit-adversarial"}
    if set(groups) != expected_names:
        raise RuntimeError(
            "GI v4 stream groups are incomplete: "
            f"expected {sorted(expected_names)}, got {sorted(groups)}"
        )
    counts = {label: 0 for label in STREAM_VALIDATION_COUNTS}
    for group in groups.values():
        group["files"].sort(key=lambda item: item["path"])
        counts[group["label"]] += len(group["files"])
    if counts != _expected_counts:
        raise RuntimeError(
            f"GI v4 stream validation counts must be {_expected_counts}, got {counts}"
        )

    validation = BASE.DOWNLOADS["validation_features"]
    return {
        "schema_version": 1,
        "human_audio_used": False,
        "generation": {
            "generated_manifest_sha256": generated_manifest_sha256,
            "plan_sha256": plan_sha256,
        },
        "generic_negative": {
            "path": validation.filename,
            "sha256": validation.sha256,
            "bytes": validation.size,
            "shape": VALIDATION_FEATURE_SHAPE,
            "dtype": "float32",
            "declared_hours": 11.3,
            "source": "openwakeword_false_positive_validation",
        },
        "groups": [groups[name] for name in sorted(groups)],
    }


def _load_training_metrics(workspace: Path) -> dict[str, object]:
    path = workspace / BASE.TRAINING_METRICS
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Missing or unsafe GI v4 training metrics: {path}")
    try:
        record = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"Invalid GI v4 training metrics JSON: {path}") from error
    keys = {
        "schema_version",
        "model_name",
        "config_sha256",
        "trainer_sha256",
        "false_positive_validation_hours",
        "metric_threshold",
        "targets",
        "history",
        "checkpoints",
        "selection",
        "final",
        "model_files",
        "passed",
    }
    if type(record) is not dict or set(record) != keys:
        raise RuntimeError("GI v4 training metrics have an unexpected schema")
    if (
        record["schema_version"] != 2
        or record["model_name"] != BASE.MODEL_NAME
        or record["config_sha256"] != BASE.CONFIG_SHA256
        or record["trainer_sha256"] != TRAIN_PATCHED_SHA256
        or record["false_positive_validation_hours"] != 11.3
        or record["metric_threshold"] != 0.5
        or record["targets"] != BASE.TRAINING_TARGETS
    ):
        raise RuntimeError("GI v4 training metrics have unexpected provenance or targets")
    history = record["history"]
    history_keys = {
        "loss",
        "recall",
        "val_accuracy",
        "val_recall",
        "val_n_fp",
        "val_fp_per_hr",
    }
    if type(history) is not dict or set(history) != history_keys:
        raise RuntimeError("GI v4 training metrics have incomplete history")
    for name, values in history.items():
        if type(values) is not list or not values:
            raise RuntimeError(f"GI v4 training history {name} is empty or invalid")
        for index, value in enumerate(values):
            BASE._finite_number(
                value,
                f"history.{name}[{index}]",
                minimum=0,
                maximum=1 if name in {"recall", "val_accuracy", "val_recall"} else None,
            )
    validation_lengths = {
        len(history[name]) for name in ("val_accuracy", "val_recall", "val_n_fp", "val_fp_per_hr")
    }
    if len(validation_lengths) != 1:
        raise RuntimeError("GI v4 training validation history lengths differ")
    checkpoints = record["checkpoints"]
    checkpoint_keys = {
        "checkpoint_index",
        "training_step_ndx",
        "accuracy",
        "recall",
        "false_positives",
        "false_positives_per_hour",
        "eligible",
    }
    if type(checkpoints) is not list or not checkpoints:
        raise RuntimeError("GI v4 training checkpoints are empty or invalid")
    eligible: list[int] = []
    for index, checkpoint in enumerate(checkpoints):
        if type(checkpoint) is not dict or set(checkpoint) != checkpoint_keys:
            raise RuntimeError(f"GI v4 checkpoint {index} has an unexpected schema")
        if (
            type(checkpoint["checkpoint_index"]) is not int
            or checkpoint["checkpoint_index"] != index
            or type(checkpoint["training_step_ndx"]) is not int
            or checkpoint["training_step_ndx"] < 0
            or type(checkpoint["false_positives"]) is not int
            or checkpoint["false_positives"] < 0
        ):
            raise RuntimeError(f"GI v4 checkpoint {index} has invalid indexes or counts")
        accuracy = BASE._finite_number(
            checkpoint["accuracy"], f"checkpoints[{index}].accuracy", minimum=0, maximum=1
        )
        recall = BASE._finite_number(
            checkpoint["recall"], f"checkpoints[{index}].recall", minimum=0, maximum=1
        )
        false_positives = BASE._finite_number(
            checkpoint["false_positives"],
            f"checkpoints[{index}].false_positives",
            minimum=0,
        )
        fp_per_hour = BASE._finite_number(
            checkpoint["false_positives_per_hour"],
            f"checkpoints[{index}].false_positives_per_hour",
            minimum=0,
        )
        expected_eligible = (
            accuracy >= BASE.TRAINING_TARGETS["minimum_accuracy"]
            and recall >= BASE.TRAINING_TARGETS["minimum_recall"]
            and fp_per_hour <= BASE.TRAINING_TARGETS["maximum_false_positives_per_hour"]
        )
        if type(checkpoint["eligible"]) is not bool or checkpoint["eligible"] != expected_eligible:
            raise RuntimeError(f"GI v4 checkpoint {index} has a wrong eligibility result")
        if expected_eligible:
            eligible.append(index)
        checkpoint["_selection_key"] = (
            recall,
            accuracy,
            -fp_per_hour,
            -false_positives,
            -index,
        )
    if not eligible:
        raise RuntimeError("GI v4 training report contains no eligible checkpoint")
    selected = max(eligible, key=lambda index: checkpoints[index]["_selection_key"])
    for checkpoint in checkpoints:
        checkpoint.pop("_selection_key")
    expected_selection = {
        "method": "max_recall_then_accuracy_then_min_fp_then_earliest",
        "evaluated_count": len(checkpoints),
        "eligible_count": len(eligible),
        "selected_checkpoint_index": selected,
        "passed": True,
    }
    if record["selection"] != expected_selection:
        raise RuntimeError("GI v4 training selection does not match the checkpoint scores")
    final = record["final"]
    if type(final) is not dict or set(final) != {
        "accuracy",
        "recall",
        "false_positives_per_hour",
    }:
        raise RuntimeError("GI v4 final training metrics have an unexpected schema")
    accuracy = BASE._finite_number(final["accuracy"], "final.accuracy", minimum=0, maximum=1)
    recall = BASE._finite_number(final["recall"], "final.recall", minimum=0, maximum=1)
    fp_per_hour = BASE._finite_number(
        final["false_positives_per_hour"], "final.false_positives_per_hour", minimum=0
    )
    passed = (
        accuracy >= BASE.TRAINING_TARGETS["minimum_accuracy"]
        and recall >= BASE.TRAINING_TARGETS["minimum_recall"]
        and fp_per_hour <= BASE.TRAINING_TARGETS["maximum_false_positives_per_hour"]
    )
    if record["passed"] is not True or not passed:
        raise RuntimeError("GI v4 final training metrics do not pass every target")
    onnx = workspace / BASE.ONNX_PATH
    external = workspace / BASE.ONNX_DATA_PATH
    if onnx.is_symlink() or not onnx.is_file():
        raise RuntimeError(f"Missing or unsafe GI v4 ONNX model: {onnx}")
    model_files = {f"{BASE.MODEL_NAME}.onnx": BASE.sha256(onnx)}
    if external.is_symlink() or (external.exists() and not external.is_file()):
        raise RuntimeError(f"Unsafe GI v4 ONNX external data: {external}")
    if external.is_file():
        model_files[f"{BASE.MODEL_NAME}.onnx.data"] = BASE.sha256(external)
    if record["model_files"] != model_files:
        raise RuntimeError("GI v4 training metrics do not match the selected ONNX model")
    return record


def _validate_generated_outputs(workspace: Path) -> dict[str, object]:
    root = workspace / BASE.WORK_DIR
    plan_path = root / "gi-v4-synthesis-plan.json"
    manifest_path = root / "gi-v4-generated-manifest.json"
    try:
        plan = json.loads(plan_path.read_text())
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError("Missing or invalid GI v4 synthesis evidence") from error
    synth = _load(SYNTHESIZER, "gi_v4_synthesize_validation")
    verified = synth.verify_generated_stage(plan, root, _expected_piper())
    if verified != manifest:
        raise RuntimeError("GI v4 generated manifest changed during validation")
    expected_counts = {
        "positive_train": 20_000,
        "positive_test": 2_000,
        "negative_train": 20_000,
        "negative_test": 2_000,
    }
    if manifest.get("counts") != expected_counts:
        raise RuntimeError(f"Wrong GI v4 generated counts: {manifest.get('counts')}")
    return verified


def _build_stream_input(workspace: Path) -> Path:
    generated = _validate_generated_outputs(workspace)
    root = workspace / BASE.WORK_DIR
    plan_path = root / "gi-v4-synthesis-plan.json"
    generated_path = root / "gi-v4-generated-manifest.json"
    try:
        plan = json.loads(plan_path.read_text())
        validation_speakers = plan["speaker_ids"]["val"]
        records = generated["records"]
        plan_sha256 = generated["plan_sha256"]
    except (json.JSONDecodeError, KeyError, OSError, TypeError) as error:
        raise RuntimeError("GI v4 synthesis evidence cannot build the stream gate") from error
    manifest = _stream_manifest_from_records(
        records,
        validation_speakers,
        generated_manifest_sha256=BASE.sha256(generated_path),
        plan_sha256=plan_sha256,
    )
    encoded = json.dumps(
        manifest,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    path = workspace / STREAM_INPUT
    BASE.atomic_text(path, encoded + "\n")
    return path


def _require_stream_report(workspace: Path) -> dict[str, object]:
    report_path = workspace / STREAM_REPORT
    manifest_path = workspace / STREAM_INPUT
    model_path = workspace / BASE.TFLITE_PATH
    generated_path = workspace / BASE.WORK_DIR / "gi-v4-generated-manifest.json"
    for name, path in {
        "report": report_path,
        "input manifest": manifest_path,
        "model": model_path,
        "generated manifest": generated_path,
    }.items():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Missing or unsafe GI v4 stream {name}: {path}")

    evaluator = _load(STREAM_EVALUATOR, "gi_v4_stream_report_validation")
    raw = report_path.read_bytes()
    try:
        report = json.loads(raw)
        generated = json.loads(generated_path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError("Missing or invalid GI v4 stream evidence") from error
    if evaluator.canonical_json(report) != raw:
        raise RuntimeError("GI v4 stream report is not canonical JSON")
    try:
        evaluator.verify_report(report)
    except ValueError as error:
        raise RuntimeError("GI v4 stream report failed verification") from error
    if report["passed"] is not True:
        raise RuntimeError("GI v4 stream report did not pass every gate")

    expected_model = {
        "filename": model_path.name,
        "bytes": model_path.stat().st_size,
        "sha256": BASE.sha256(model_path),
    }
    expected_input = {
        "manifest_sha256": BASE.sha256(manifest_path),
        "generated_manifest_sha256": BASE.sha256(generated_path),
        "plan_sha256": generated.get("plan_sha256"),
    }
    if report["model"] != expected_model or any(
        report["input"].get(name) != value for name, value in expected_input.items()
    ):
        raise RuntimeError("GI v4 stream report does not match the current candidate")
    feature = BASE.DOWNLOADS["validation_features"]
    if (
        report["input"]["generic_feature_sha256"] != feature.sha256
        or report["input"]["generic_feature_bytes"] != feature.size
        or report["input"]["generic_feature_shape"] != VALIDATION_FEATURE_SHAPE
    ):
        raise RuntimeError("GI v4 stream report does not match the pinned negative features")
    return report


def _verify_candidate(workspace: Path) -> None:
    COMMON_VERIFY_CANDIDATE(workspace)
    feature = BASE.DOWNLOADS["validation_features"]
    feature_path = workspace / feature.filename
    BASE.download(feature, feature_path)
    BASE.verify_file(feature_path, feature)
    manifest = _build_stream_input(workspace)
    BASE.run(
        [
            str(workspace / ".venv-convert/bin/python"),
            str(STREAM_EVALUATOR),
            "--manifest",
            str(manifest),
            "--input-root",
            str(workspace),
            "--model",
            str(workspace / BASE.TFLITE_PATH),
            "--output",
            str(workspace / STREAM_REPORT),
        ],
        cwd=workspace,
    )
    _require_stream_report(workspace)


def _extra_bundle_artifacts(workspace: Path, checkpoint_dir: Path) -> dict[str, Path]:
    del checkpoint_dir
    return {
        "reports/gi-v4-synthesis-plan.json": (
            workspace / BASE.WORK_DIR / "gi-v4-synthesis-plan.json"
        ),
        "reports/gi-v4-generated-manifest.json": (
            workspace / BASE.WORK_DIR / "gi-v4-generated-manifest.json"
        ),
        f"reports/{STREAM_INPUT.name}": workspace / STREAM_INPUT,
        f"reports/{STREAM_REPORT.name}": workspace / STREAM_REPORT,
        f"workflow/{COMMON_DRIVER.name}": COMMON_DRIVER,
        f"workflow/{PLAN_SCRIPT.name}": PLAN_SCRIPT,
        f"workflow/{SYNTHESIZER.name}": SYNTHESIZER,
        f"workflow/{STREAM_EVALUATOR.name}": STREAM_EVALUATOR,
        f"patches/{PIPER_PATCH.name}": PIPER_PATCH,
        f"patches/{TRAIN_PATCH.name}": TRAIN_PATCH,
        "patched-sources/piper-models.py": (
            workspace / "piper-sample-generator/piper_train/vits/models.py"
        ),
    }


def _extra_expected_hashes() -> dict[str, str]:
    return {
        f"workflow/{COMMON_DRIVER.name}": BASE.sha256(COMMON_DRIVER),
        f"workflow/{PLAN_SCRIPT.name}": BASE.sha256(PLAN_SCRIPT),
        f"workflow/{SYNTHESIZER.name}": BASE.sha256(SYNTHESIZER),
        f"workflow/{STREAM_EVALUATOR.name}": BASE.sha256(STREAM_EVALUATOR),
        f"patches/{PIPER_PATCH.name}": PIPER_PATCH_SHA256,
        f"patches/{TRAIN_PATCH.name}": TRAIN_PATCH_SHA256,
        "patched-sources/piper-models.py": PIPER_MODELS_PATCHED_SHA256,
    }


def _extra_manifest_fields(workspace: Path, checkpoint_dir: Path) -> dict[str, object]:
    del checkpoint_dir
    _validate_generated_outputs(workspace)
    _build_stream_input(workspace)
    stream = _require_stream_report(workspace)
    root = workspace / BASE.WORK_DIR
    plan = root / "gi-v4-synthesis-plan.json"
    generated = root / "gi-v4-generated-manifest.json"
    record = json.loads(generated.read_text())
    return {
        "synthesis": {
            "human_audio_used": False,
            "plan": "reports/gi-v4-synthesis-plan.json",
            "plan_sha256": BASE.sha256(plan),
            "generated_manifest": "reports/gi-v4-generated-manifest.json",
            "generated_manifest_sha256": BASE.sha256(generated),
            "counts": record["counts"],
            "piper": record["piper"],
        },
        "streaming_evaluation": {
            "input": f"reports/{STREAM_INPUT.name}",
            "input_sha256": BASE.sha256(workspace / STREAM_INPUT),
            "report": f"reports/{STREAM_REPORT.name}",
            "report_file_sha256": BASE.sha256(workspace / STREAM_REPORT),
            "report_sha256": stream["report_sha256"],
            "evaluator": f"workflow/{STREAM_EVALUATOR.name}",
            "evaluator_sha256": BASE.sha256(STREAM_EVALUATOR),
            "conversion_lock_sha256": BASE.CONVERSION_LOCK_SHA256,
            "runtime": stream["runtime"],
            "settings": stream["settings"],
            "gates": stream["gates"],
            "generic_negative": stream["generic_negative"],
            "passed": True,
        },
    }


BASE._validate_generated_outputs = _validate_generated_outputs
BASE._load_training_metrics = _load_training_metrics
BASE._extra_bundle_artifacts = _extra_bundle_artifacts
BASE._extra_expected_hashes = _extra_expected_hashes
BASE._extra_manifest_fields = _extra_manifest_fields
BASE.verify_candidate = _verify_candidate


def __getattr__(name: str) -> object:
    return getattr(BASE, name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=BASE.DEFAULT_WORKSPACE)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--config", type=Path, default=BASE.DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=("all", "prepare", "generate", "augment", "train", "convert", "verify", "bundle"),
        default="all",
    )
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--internal-generate", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.internal_generate:
        _run_internal_generation(args.workspace)
        return 0
    if args.checkpoint_dir is None:
        raise SystemExit("--checkpoint-dir is required")
    plan = BASE.build_plan(args.workspace, args.checkpoint_dir, args.config)
    if args.plan or args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    BASE.require_host_runtime()
    BASE.require_checkpoint_storage(args.checkpoint_dir)
    stages = ("prepare", "generate", "augment", "train", "convert", "verify", "bundle")
    selected = stages if args.stage == "all" else (args.stage,)
    for stage in selected:
        if stage == "prepare":
            BASE.prepare(args.workspace, args.checkpoint_dir, args.config)
        elif stage in BASE.STAGE_OUTPUTS:
            BASE.run_training_stage(args.workspace, args.checkpoint_dir, stage)
        elif stage == "convert":
            BASE.convert(args.workspace, args.checkpoint_dir)
        elif stage == "verify":
            BASE.verify_candidate(args.workspace)
        elif stage == "bundle":
            BASE.bundle(args.workspace, args.checkpoint_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
