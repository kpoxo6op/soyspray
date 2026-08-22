from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/train_gi_v4_colab.py"
BASE_SCRIPT = ROOT / "scripts/train_gi_v3_colab.py"
PLAN_SCRIPT = ROOT / "scripts/gi_v4_synthesis_plan.py"
SYNTH_SCRIPT = ROOT / "scripts/gi_v4_synthesize.py"
STREAM_SCRIPT = ROOT / "scripts/gi_v4_stream_eval.py"
CONFIG = (
    ROOT
    / "playbooks/argocd/applications/home-automation/voice-assistant/models"
    / "gi-v4-training.yaml"
)


def load_driver() -> ModuleType:
    assert SCRIPT.is_file(), "missing GI v4 Colab driver"
    spec = importlib.util.spec_from_file_location("test_train_gi_v4_colab", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v4_uses_the_shared_driver_with_versioned_paths(tmp_path: Path) -> None:
    driver = load_driver()

    assert driver.COMMON_DRIVER == BASE_SCRIPT
    assert driver.DRIVER == SCRIPT
    assert driver.CANDIDATE == "gi-v4"
    assert driver.MODEL_NAME == "gi"
    assert driver.DEFAULT_CONFIG == CONFIG
    assert driver.DEFAULT_WORKSPACE == Path("/content/gi-v4")
    assert driver.CONFIG_BASENAME == "gi-v4-training.yaml"
    assert driver.MANIFEST_BASENAME == "gi-v4-manifest.json"
    assert driver.TRAINING_METRICS == Path("gi-v4-work/gi-v4-training-metrics.json")
    assert driver.TFLITE_PATH == Path("gi-v4-work/gi-v4.tflite")
    assert driver.PARITY_PATH == Path("gi-v4-work/gi-v4-parity.json")
    assert driver.STREAM_INPUT == Path("gi-v4-work/gi-v4-stream-input.json")
    assert driver.STREAM_REPORT == Path("gi-v4-work/gi-v4-stream-report.json")

    plan = driver.build_plan(tmp_path / "work", tmp_path / "checkpoints", CONFIG)
    assert plan["workspace"].endswith("/work")
    assert plan["config"]["staged"].endswith("/gi-v4-training.yaml")
    assert plan["stages"][1]["operation"][-4:] == [
        str(SCRIPT),
        "--internal-generate",
        "--workspace",
        str(tmp_path / "work"),
    ]
    assert plan["stages"][-1]["manifest"].endswith("/gi-v4-manifest.json")
    assert all("gi-v3-work" not in str(stage) for stage in plan["stages"])


def test_v4_generate_checkpoint_contains_plan_and_generated_manifest() -> None:
    driver = load_driver()

    assert driver.STAGE_OUTPUTS["generate"][-2:] == (
        Path("gi-v4-work/gi-v4-synthesis-plan.json"),
        Path("gi-v4-work/gi-v4-generated-manifest.json"),
    )
    assert set(driver.GENERATED_COUNTS.values()) == {2_000, 20_000}
    assert all(str(path).startswith("gi-v4-work/") for path in driver.GENERATED_COUNTS)


def test_v4_checkpoint_provenance_binds_both_drivers_and_generation_code() -> None:
    driver = load_driver()

    record = driver._checkpoint_provenance("generate")

    assert record["driver_sha256"] == driver.sha256(SCRIPT)
    assert record["common_driver_sha256"] == driver.sha256(BASE_SCRIPT)
    assert record["synthesis_plan_sha256"] == driver.sha256(PLAN_SCRIPT)
    assert record["synthesizer_sha256"] == driver.sha256(SYNTH_SCRIPT)
    assert record["stream_evaluator_sha256"] == driver.sha256(STREAM_SCRIPT)
    assert record["candidate"] == "gi-v4"


def _generated_record(
    index: int,
    *,
    partition: str,
    class_name: str,
    text: str,
    source: str,
    first_speaker: int,
) -> dict[str, object]:
    directory = f"{class_name}_{'test' if partition == 'val' else 'train'}"
    return {
        "index": index,
        "filename": f"{index:08d}.wav",
        "partition": partition,
        "class": class_name,
        "text": text,
        "source": source,
        "speakers": [first_speaker, first_speaker + 100],
        "slerp_weight": 0.5,
        "length_scale": 1.0,
        "noise_scale": 1.0,
        "noise_scale_w": 1.0,
        "seed": index,
        "file": f"gi/{directory}/{index:08d}.wav",
        "bytes": 100,
        "sha256": f"{index + 1:064x}",
    }


def test_v4_stream_manifest_uses_validation_audio_and_pinned_generic_features() -> None:
    driver = load_driver()
    validation_speakers = list(range(10))
    records = []
    index = 0
    for text in ("gee eye", "GI"):
        for first_speaker in (0, 2, 4, 6, 8):
            records.append(
                _generated_record(
                    index,
                    partition="val",
                    class_name="positive",
                    text=text,
                    source="piper_fixed",
                    first_speaker=first_speaker,
                )
            )
            index += 1
    for text in (
        "gee",
        "eye",
        "nabu",
        "okay nabu",
        "turn on the lights",
        "turn off the lights",
    ):
        records.append(
            _generated_record(
                index,
                partition="val",
                class_name="negative",
                text=text,
                source="piper_fixed",
                first_speaker=0,
            )
        )
        index += 1
    records.append(
        _generated_record(
            index,
            partition="val",
            class_name="negative",
            text="key eye",
            source="piper_adversarial",
            first_speaker=0,
        )
    )
    index += 1
    records.append(
        _generated_record(
            index,
            partition="train",
            class_name="positive",
            text="GI",
            source="piper_fixed",
            first_speaker=1,
        )
    )

    manifest = driver._stream_manifest_from_records(
        records,
        validation_speakers,
        generated_manifest_sha256="a" * 64,
        plan_sha256="b" * 64,
        _expected_counts={"positive": 10, "explicit_negative": 7},
    )

    assert set(manifest) == {
        "schema_version",
        "human_audio_used",
        "generation",
        "generic_negative",
        "groups",
    }
    assert manifest["human_audio_used"] is False
    assert manifest["generation"] == {
        "generated_manifest_sha256": "a" * 64,
        "plan_sha256": "b" * 64,
    }
    generic = manifest["generic_negative"]
    asset = driver.DOWNLOADS["validation_features"]
    assert generic == {
        "path": asset.filename,
        "sha256": asset.sha256,
        "bytes": asset.size,
        "shape": [481_345, 96],
        "dtype": "float32",
        "declared_hours": 11.3,
        "source": "openwakeword_false_positive_validation",
    }
    groups = manifest["groups"]
    assert [group["name"] for group in groups] == sorted(group["name"] for group in groups)
    assert {group["name"] for group in groups if group["label"] == "positive"} == {
        f"positive-{spelling}-speaker-{bucket:02d}"
        for spelling in ("gee-eye", "gi")
        for bucket in range(5)
    }
    assert {group["name"] for group in groups if group["label"] == "explicit_negative"} == {
        "explicit-adversarial",
        "explicit-eye",
        "explicit-gee",
        "explicit-nabu",
        "explicit-okay-nabu",
        "explicit-turn-off-the-lights",
        "explicit-turn-on-the-lights",
    }
    files = [item for group in groups for item in group["files"]]
    assert len(files) == len(records) - 1
    assert all(item["path"].startswith("gi-v4-work/gi/") for item in files)
    assert not any("positive_train" in item["path"] for item in files)


def test_v4_build_plan_keeps_common_downstream_operations(tmp_path: Path) -> None:
    driver = load_driver()
    plan = driver.build_plan(tmp_path / "work", tmp_path / "checkpoints", CONFIG)
    stages = {stage["name"]: stage for stage in plan["stages"]}

    assert stages["augment"]["operation"][-2:] == ["--augment_clips", "--overwrite"]
    assert stages["train"]["operation"][-1] == "--train_model"
    assert stages["convert"]["operation"][0].endswith("/.venv-convert/bin/onnx2tf")
    assert stages["verify"]["limits"] == {
        "input_shape": [1, 16, 96],
        "seeded_samples": 32,
        "max_absolute_error": 1e-5,
        "minimum_cosine_similarity": 0.99999,
        "streaming": {
            "threshold": 0.65,
            "trigger_level": 2,
            "minimum_positive_group_recall": 0.95,
            "maximum_explicit_negative_activations": 0,
            "maximum_generic_negative_activations_per_hour": 0.2,
        },
    }


def test_loading_v4_does_not_change_a_fresh_v3_module() -> None:
    load_driver()
    spec = importlib.util.spec_from_file_location("fresh_v3_after_v4", BASE_SCRIPT)
    assert spec is not None and spec.loader is not None
    v3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v3)

    assert v3.CANDIDATE == "gi-v3"
    assert v3.DEFAULT_WORKSPACE == Path("/content/gi-v3")
    assert v3._checkpoint_path(Path("/tmp/checkpoints"), "onnx").name == "gi-v3-onnx.tar"


def _valid_training_report(driver: ModuleType, workspace: Path) -> dict[str, object]:
    onnx = workspace / driver.ONNX_PATH
    onnx.parent.mkdir(parents=True)
    onnx.write_bytes(b"selected model")
    checkpoints = [
        {
            "checkpoint_index": 0,
            "training_step_ndx": 100,
            "accuracy": 0.95,
            "recall": 0.95,
            "false_positives": 2,
            "false_positives_per_hour": 0.2,
            "eligible": True,
        },
        {
            "checkpoint_index": 1,
            "training_step_ndx": 200,
            "accuracy": 0.96,
            "recall": 0.96,
            "false_positives": 2,
            "false_positives_per_hour": 0.2,
            "eligible": True,
        },
        {
            "checkpoint_index": 2,
            "training_step_ndx": 300,
            "accuracy": 0.96,
            "recall": 0.96,
            "false_positives": 1,
            "false_positives_per_hour": 0.1,
            "eligible": True,
        },
    ]
    return {
        "schema_version": 2,
        "model_name": "gi",
        "config_sha256": driver.CONFIG_SHA256,
        "trainer_sha256": driver.TRAIN_PATCHED_SHA256,
        "false_positive_validation_hours": 11.3,
        "metric_threshold": 0.5,
        "targets": driver.TRAINING_TARGETS,
        "history": {
            "loss": [0.1],
            "recall": [0.96],
            "val_accuracy": [0.96],
            "val_recall": [0.96],
            "val_n_fp": [1],
            "val_fp_per_hr": [0.1],
        },
        "checkpoints": checkpoints,
        "selection": {
            "method": "max_recall_then_accuracy_then_min_fp_then_earliest",
            "evaluated_count": 3,
            "eligible_count": 3,
            "selected_checkpoint_index": 2,
            "passed": True,
        },
        "final": {
            "accuracy": 0.96,
            "recall": 0.96,
            "false_positives_per_hour": 0.1,
        },
        "model_files": {"gi.onnx": driver.sha256(onnx)},
        "passed": True,
    }


def test_v4_training_report_recomputes_absolute_checkpoint_selection(tmp_path: Path) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    report = _valid_training_report(driver, workspace)
    path = workspace / driver.TRAINING_METRICS
    path.write_text(json.dumps(report))

    assert driver._load_training_metrics(workspace) == report

    report["selection"]["selected_checkpoint_index"] = 0
    path.write_text(json.dumps(report))
    with pytest.raises(RuntimeError, match="selection"):
        driver._load_training_metrics(workspace)


def test_v4_training_report_uses_inclusive_gates_and_rejects_false_flags(
    tmp_path: Path,
) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    report = _valid_training_report(driver, workspace)
    report["checkpoints"] = [report["checkpoints"][0]]
    report["selection"] = {
        "method": "max_recall_then_accuracy_then_min_fp_then_earliest",
        "evaluated_count": 1,
        "eligible_count": 1,
        "selected_checkpoint_index": 0,
        "passed": True,
    }
    report["final"] = {
        "accuracy": 0.95,
        "recall": 0.95,
        "false_positives_per_hour": 0.2,
    }
    path = workspace / driver.TRAINING_METRICS
    path.write_text(json.dumps(report))

    assert driver._load_training_metrics(workspace)["passed"] is True

    report["checkpoints"][0]["eligible"] = False
    path.write_text(json.dumps(report))
    with pytest.raises(RuntimeError, match="eligibility"):
        driver._load_training_metrics(workspace)


def test_v4_trainer_patch_removes_averaging_and_exports_only_a_passing_selection() -> None:
    driver = load_driver()
    patch = driver.TRAIN_PATCH.read_text()

    assert "Merging checkpoints" in patch
    assert "-        return combined_model" in patch
    assert '+        return selected_model if self.selection["passed"] else None' in patch
    assert "+        if not passed:" in patch
    assert "No GI v4 training checkpoint met every configured target" in patch


def test_v4_verify_runs_parity_and_the_pinned_stream_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    manifest = workspace / driver.STREAM_INPUT
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}\n")
    events = []

    monkeypatch.setattr(
        driver, "COMMON_VERIFY_CANDIDATE", lambda path: events.append(("parity", path))
    )
    monkeypatch.setattr(
        driver.BASE,
        "download",
        lambda asset, path: events.append(("download", asset.filename, path)),
    )
    monkeypatch.setattr(
        driver.BASE,
        "verify_file",
        lambda path, asset: events.append(("verify-file", path, asset.filename)),
    )
    monkeypatch.setattr(driver, "_build_stream_input", lambda path: manifest)
    monkeypatch.setattr(
        driver.BASE,
        "run",
        lambda command, cwd=None: events.append(("run", command, cwd)),
    )
    monkeypatch.setattr(
        driver,
        "_require_stream_report",
        lambda path: events.append(("report", path)) or {"passed": True},
    )

    driver._verify_candidate(workspace)

    asset = driver.DOWNLOADS["validation_features"]
    assert events[0] == ("parity", workspace)
    assert events[1] == ("download", asset.filename, workspace / asset.filename)
    assert events[2] == ("verify-file", workspace / asset.filename, asset.filename)
    command = events[3][1]
    assert command == [
        str(workspace / ".venv-convert/bin/python"),
        str(STREAM_SCRIPT),
        "--manifest",
        str(manifest),
        "--input-root",
        str(workspace),
        "--model",
        str(workspace / driver.TFLITE_PATH),
        "--output",
        str(workspace / driver.STREAM_REPORT),
    ]
    assert events[3][2] == workspace
    assert events[4] == ("report", workspace)


def test_v4_bundle_inputs_include_and_bind_stream_evidence(tmp_path: Path) -> None:
    driver = load_driver()
    artifacts = driver._extra_bundle_artifacts(tmp_path, tmp_path / "checkpoints")

    assert artifacts[f"reports/{driver.STREAM_INPUT.name}"] == tmp_path / driver.STREAM_INPUT
    assert artifacts[f"reports/{driver.STREAM_REPORT.name}"] == tmp_path / driver.STREAM_REPORT
    assert artifacts[f"workflow/{STREAM_SCRIPT.name}"] == STREAM_SCRIPT
    assert driver._extra_expected_hashes()[f"workflow/{STREAM_SCRIPT.name}"] == driver.sha256(
        STREAM_SCRIPT
    )
