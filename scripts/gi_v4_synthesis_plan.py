#!/usr/bin/env python3
"""Build and verify the deterministic GI V4 synthetic-audio plan."""

from __future__ import annotations

import itertools
import json
import random
from typing import Any

SCHEMA_VERSION = 1
NUM_SPEAKERS = 904
VALIDATION_SPEAKERS = 90
SPEAKER_SPLIT_SEED = 20260815
PARTITION_SEEDS = {"train": 20260816, "val": 20260817}
PIPER_CHECKPOINT = "en_US-libritts_r-medium.pt"
PIPER_CHECKPOINT_SHA256 = "e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6"
SLERP_WEIGHTS = (0.0, 0.5, 1.0)
LENGTH_SCALES = (0.75, 1.0, 1.25)
NOISE = {"train": (0.98, 0.98), "val": (1.0, 1.0)}
POSITIVE_QUOTAS = {
    "train": {"gee eye": 10_000, "GI": 10_000},
    "val": {"gee eye": 1_000, "GI": 1_000},
}
NEGATIVE_QUOTAS = {
    "train": {
        "gee": 2_000,
        "eye": 2_000,
        "nabu": 2_000,
        "okay nabu": 2_000,
        "turn on the lights": 1_000,
        "turn off the lights": 1_000,
    },
    "val": {
        "gee": 200,
        "eye": 200,
        "nabu": 200,
        "okay nabu": 200,
        "turn on the lights": 100,
        "turn off the lights": 100,
    },
}
ADVERSARIAL_COUNTS = {"train": 10_000, "val": 1_000}


def _validate_texts(name: str, texts: object, count: int) -> list[str]:
    if type(texts) is not list:
        raise TypeError(f"{name} must be an explicit list of text strings")
    if len(texts) != count:
        raise ValueError(f"{name} must contain exactly {count} strings")

    result: list[str] = []
    for text in texts:
        if type(text) is not str or not text or text != text.strip():
            raise ValueError(f"{name} entries must be non-empty trimmed strings")
        folded = text.casefold()
        if "g i" in folded or "g.i." in folded:
            raise ValueError(f"{name} must not contain G I or G.I.")
        if (
            "/" in text
            or "\\" in text
            or folded.endswith(
                (
                    ".wav",
                    ".wave",
                    ".mp3",
                    ".flac",
                    ".ogg",
                    ".oga",
                    ".opus",
                    ".m4a",
                    ".aac",
                    ".aiff",
                    ".aif",
                    ".wma",
                    ".webm",
                )
            )
        ):
            raise ValueError(f"{name} accepts text, not paths or audio files")
        result.append(text)
    return result


def _speaker_split(num_speakers: int) -> dict[str, list[int]]:
    if type(num_speakers) is not int or num_speakers != NUM_SPEAKERS:
        raise ValueError(f"num_speakers must be {NUM_SPEAKERS}")
    speaker_ids = list(range(num_speakers))
    random.Random(SPEAKER_SPLIT_SEED).shuffle(speaker_ids)
    validation = set(speaker_ids[:VALIDATION_SPEAKERS])
    return {
        "train": sorted(set(speaker_ids) - validation),
        "val": sorted(validation),
    }


def _specifications(
    partition: str,
    class_name: str,
    adversarial: list[str],
) -> list[tuple[str, str]]:
    if class_name == "positive":
        quotas = POSITIVE_QUOTAS[partition]
        return [(text, "piper_fixed") for text, count in quotas.items() for _ in range(count)]
    fixed = [
        (text, "piper_fixed")
        for text, count in NEGATIVE_QUOTAS[partition].items()
        for _ in range(count)
    ]
    return fixed + [(text, "piper_adversarial") for text in adversarial]


def _build_plan(
    adversarial_train: list[str],
    adversarial_val: list[str],
    num_speakers: int,
) -> dict[str, Any]:
    speaker_ids = _speaker_split(num_speakers)
    adversarial = {"train": adversarial_train, "val": adversarial_val}
    records: list[dict[str, Any]] = []

    for partition in ("train", "val"):
        rng = random.Random(PARTITION_SEEDS[partition])
        noise_scale, noise_scale_w = NOISE[partition]
        for class_name in ("positive", "negative"):
            specifications = _specifications(partition, class_name, adversarial[partition])
            rng.shuffle(specifications)
            settings = list(itertools.product(SLERP_WEIGHTS, LENGTH_SCALES))
            rng.shuffle(settings)
            for offset, (text, source) in enumerate(specifications):
                index = len(records)
                speakers = rng.sample(speaker_ids[partition], 2)
                slerp_weight, length_scale = settings[offset % len(settings)]
                records.append(
                    {
                        "index": index,
                        "filename": f"{index:08d}.wav",
                        "partition": partition,
                        "class": class_name,
                        "text": text,
                        "source": source,
                        "speakers": speakers,
                        "slerp_weight": slerp_weight,
                        "length_scale": length_scale,
                        "noise_scale": noise_scale,
                        "noise_scale_w": noise_scale_w,
                        "seed": rng.getrandbits(64),
                    }
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "human_audio_used": False,
        "piper": {
            "checkpoint_filename": PIPER_CHECKPOINT,
            "checkpoint_sha256": PIPER_CHECKPOINT_SHA256,
            "num_speakers": num_speakers,
        },
        "seeds": {
            "speaker_split": SPEAKER_SPLIT_SEED,
            **PARTITION_SEEDS,
        },
        "speaker_ids": speaker_ids,
        "adversarial_texts": adversarial,
        "records": records,
    }


def build_plan(
    adversarial_train: object,
    adversarial_val: object,
    *,
    num_speakers: int = NUM_SPEAKERS,
) -> dict[str, Any]:
    """Return a deterministic plan from explicit synthetic adversarial texts."""
    train = _validate_texts("adversarial_train", adversarial_train, ADVERSARIAL_COUNTS["train"])
    val = _validate_texts("adversarial_val", adversarial_val, ADVERSARIAL_COUNTS["val"])
    return _build_plan(train, val, num_speakers)


def _canonical_bytes(plan: object) -> bytes:
    return (
        json.dumps(
            plan,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def verify_plan(plan: object) -> None:
    """Fail closed unless *plan* is exactly reproducible from its text lists."""
    if type(plan) is not dict:
        raise TypeError("plan must be a JSON object")
    adversarial = plan.get("adversarial_texts")
    if type(adversarial) is not dict or set(adversarial) != {"train", "val"}:
        raise ValueError("plan must contain explicit train and val adversarial texts")
    piper = plan.get("piper")
    if type(piper) is not dict:
        raise ValueError("plan must contain Piper metadata")
    train = _validate_texts("adversarial_train", adversarial["train"], ADVERSARIAL_COUNTS["train"])
    val = _validate_texts("adversarial_val", adversarial["val"], ADVERSARIAL_COUNTS["val"])
    expected = _build_plan(train, val, piper.get("num_speakers"))
    try:
        actual_bytes = _canonical_bytes(plan)
    except (TypeError, ValueError) as error:
        raise ValueError("plan must contain only finite JSON values") from error
    if actual_bytes != _canonical_bytes(expected):
        raise ValueError("plan does not match the deterministic GI V4 plan")


def canonical_json(plan: object) -> bytes:
    """Verify and encode a plan as canonical UTF-8 JSON with one final newline."""
    verify_plan(plan)
    return _canonical_bytes(plan)
