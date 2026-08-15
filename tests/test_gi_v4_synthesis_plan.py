from __future__ import annotations

import importlib.util
import random
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gi_v4_synthesis_plan.py"


def _load_module() -> ModuleType:
    assert SCRIPT.is_file(), "missing GI V4 synthesis plan helper"
    spec = importlib.util.spec_from_file_location("gi_v4_synthesis_plan", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _adversarial(prefix: str, count: int) -> list[str]:
    return [f"{prefix} {index:05d}" for index in range(count)]


@pytest.fixture(scope="module")
def module() -> ModuleType:
    return _load_module()


@pytest.fixture(scope="module")
def adversarial_train() -> list[str]:
    return _adversarial("adversarial train", 10_000)


@pytest.fixture(scope="module")
def adversarial_val() -> list[str]:
    return _adversarial("adversarial val", 1_000)


@pytest.fixture(scope="module")
def plan(
    module: ModuleType,
    adversarial_train: list[str],
    adversarial_val: list[str],
) -> dict[str, object]:
    return module.build_plan(adversarial_train, adversarial_val)


def test_plan_is_canonical_and_has_exact_dataset_counts(
    module: ModuleType,
    plan: dict[str, object],
    adversarial_train: list[str],
    adversarial_val: list[str],
) -> None:
    first = plan
    second = module.build_plan(adversarial_train, adversarial_val)

    assert module.canonical_json(first) == module.canonical_json(second)
    assert module.canonical_json(first).endswith(b"\n")
    counts = {
        (partition, class_name): sum(
            record["partition"] == partition and record["class"] == class_name
            for record in first["records"]
        )
        for partition in ("train", "val")
        for class_name in ("positive", "negative")
    }
    assert counts == {
        ("train", "positive"): 20_000,
        ("train", "negative"): 20_000,
        ("val", "positive"): 2_000,
        ("val", "negative"): 2_000,
    }
    module.verify_plan(first)


def test_metadata_and_seeded_speaker_split_are_exact(
    plan: dict[str, object],
) -> None:
    assert plan["schema_version"] == 1
    assert plan["human_audio_used"] is False
    assert plan["piper"] == {
        "checkpoint_filename": "en_US-libritts_r-medium.pt",
        "checkpoint_sha256": ("e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6"),
        "num_speakers": 904,
    }
    assert plan["seeds"] == {
        "speaker_split": 20260815,
        "train": 20260816,
        "val": 20260817,
    }

    shuffled = list(range(904))
    random.Random(20260815).shuffle(shuffled)
    expected_val = set(shuffled[:90])
    speaker_ids = plan["speaker_ids"]
    assert set(speaker_ids["val"]) == expected_val
    assert len(speaker_ids["val"]) == 90
    assert len(speaker_ids["train"]) == 814
    assert set(speaker_ids["train"]).isdisjoint(speaker_ids["val"])
    assert set(speaker_ids["train"]) | set(speaker_ids["val"]) == set(range(904))


def test_records_have_exact_schema_quotas_names_and_settings(
    plan: dict[str, object],
    adversarial_train: list[str],
    adversarial_val: list[str],
) -> None:
    records = plan["records"]
    speaker_ids = {key: set(value) for key, value in plan["speaker_ids"].items()}
    record_keys = {
        "index",
        "filename",
        "partition",
        "class",
        "text",
        "source",
        "speakers",
        "slerp_weight",
        "length_scale",
        "noise_scale",
        "noise_scale_w",
        "seed",
    }
    settings: dict[tuple[str, str], set[tuple[float, float]]] = defaultdict(set)
    fixed: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    adversarial: dict[str, list[str]] = defaultdict(list)

    for index, record in enumerate(records):
        assert set(record) == record_keys
        assert record["index"] == index
        assert record["filename"] == f"{index:08d}.wav"
        assert record["partition"] in {"train", "val"}
        assert record["class"] in {"positive", "negative"}
        assert record["source"] in {"piper_fixed", "piper_adversarial"}
        assert "g i" not in record["text"].casefold()
        assert "g.i." not in record["text"].casefold()
        assert len(record["speakers"]) == 2
        assert record["speakers"][0] != record["speakers"][1]
        assert set(record["speakers"]) <= speaker_ids[record["partition"]]
        assert record["slerp_weight"] in {0.0, 0.5, 1.0}
        assert record["length_scale"] in {0.75, 1.0, 1.25}
        expected_noise = (0.98, 0.98) if record["partition"] == "train" else (1.0, 1.0)
        assert (record["noise_scale"], record["noise_scale_w"]) == expected_noise
        assert type(record["seed"]) is int and 0 <= record["seed"] < 2**64
        settings[(record["partition"], record["class"])].add(
            (record["slerp_weight"], record["length_scale"])
        )
        if record["source"] == "piper_fixed":
            fixed[(record["partition"], record["class"])][record["text"]] += 1
        else:
            assert record["class"] == "negative"
            adversarial[record["partition"]].append(record["text"])

    expected_settings = {
        (slerp, length) for slerp in (0.0, 0.5, 1.0) for length in (0.75, 1.0, 1.25)
    }
    assert all(actual == expected_settings for actual in settings.values())
    assert fixed == {
        ("train", "positive"): Counter({"gee eye": 10_000, "GI": 10_000}),
        ("val", "positive"): Counter({"gee eye": 1_000, "GI": 1_000}),
        ("train", "negative"): Counter(
            {
                "gee": 2_000,
                "eye": 2_000,
                "nabu": 2_000,
                "okay nabu": 2_000,
                "turn on the lights": 1_000,
                "turn off the lights": 1_000,
            }
        ),
        ("val", "negative"): Counter(
            {
                "gee": 200,
                "eye": 200,
                "nabu": 200,
                "okay nabu": 200,
                "turn on the lights": 100,
                "turn off the lights": 100,
            }
        ),
    }
    assert Counter(adversarial["train"]) == Counter(adversarial_train)
    assert Counter(adversarial["val"]) == Counter(adversarial_val)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seed", -1),
        ("source", "human_recording"),
        ("filename", "../../human.wav"),
        ("slerp_weight", 0.25),
        ("unexpected", True),
    ],
)
def test_verify_rejects_record_corruption(
    module: ModuleType,
    plan: dict[str, object],
    field: str,
    value: object,
) -> None:
    damaged = plan.copy()
    damaged["records"] = list(plan["records"])
    damaged["records"][0] = dict(damaged["records"][0])
    damaged["records"][0][field] = value

    with pytest.raises(ValueError):
        module.verify_plan(damaged)


@pytest.mark.parametrize(
    "bad_text",
    ["G I", "please say G.I.", "../../recording.wav", "sample.flac"],
)
def test_builder_rejects_forbidden_spelling_paths_and_audio(
    module: ModuleType,
    adversarial_train: list[str],
    adversarial_val: list[str],
    bad_text: str,
) -> None:
    damaged = adversarial_val.copy()
    damaged[0] = bad_text

    with pytest.raises(ValueError):
        module.build_plan(adversarial_train, damaged)


def test_builder_requires_explicit_text_lists(
    module: ModuleType,
    adversarial_val: list[str],
) -> None:
    with pytest.raises(TypeError):
        module.build_plan(("not", "a", "list"), adversarial_val)
    with pytest.raises(ValueError):
        module.build_plan([Path("human.wav")] * 10_000, adversarial_val)
