#!/usr/bin/env python3
"""Train a private GI wake-word model from one repeated-utterance recording."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scipy import ndimage, signal
from scipy.io import wavfile


SAMPLE_RATE = 16_000
CLIP_SAMPLES = 32_000
INPUT_SHAPE = (16, 96)
PRODUCTION_THRESHOLD = 0.65


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_utterances(path: Path) -> tuple[list[np.ndarray], np.ndarray]:
    sample_rate, samples = wavfile.read(path)
    if sample_rate != SAMPLE_RATE or samples.ndim != 1 or samples.dtype != np.int16:
        raise RuntimeError("Voice input must be mono 16 kHz signed 16-bit PCM")
    audio = samples.astype(np.float32) / 32768.0
    envelope = ndimage.uniform_filter1d(np.abs(audio), size=320)
    threshold = max(float(np.quantile(envelope, 0.35)) * 3.0, 0.012)
    active = envelope >= threshold

    edges = np.diff(np.pad(active.astype(np.int8), (1, 1)))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    merged: list[list[int]] = []
    for start, end in zip(starts, ends, strict=True):
        if merged and start - merged[-1][1] <= 4_000:
            merged[-1][1] = int(end)
        else:
            merged.append([int(start), int(end)])

    utterances = [
        audio[max(0, start - 1_600) : min(len(audio), end + 1_600)]
        for start, end in merged
        if end - start >= 3_200
    ]
    if not 6 <= len(utterances) <= 32:
        raise RuntimeError(f"Expected 6 to 32 repeated utterances, found {len(utterances)}")

    speech_mask = np.zeros(len(audio), dtype=bool)
    for start, end in merged:
        speech_mask[max(0, start - 800) : min(len(audio), end + 800)] = True
    room_noise = audio[~speech_mask]
    if len(room_noise) < 1_600:
        room_noise = np.zeros(1_600, dtype=np.float32)
    return utterances, room_noise


def augmented_clips(
    utterances: list[np.ndarray], room_noise: np.ndarray, count: int, seed: int
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    clips = np.zeros((count, CLIP_SAMPLES), dtype=np.int16)
    for index in range(count):
        speech = utterances[int(rng.integers(len(utterances)))]
        speed = float(rng.uniform(0.90, 1.10))
        speech = signal.resample(speech, max(1, int(len(speech) / speed))).astype(np.float32)
        speech *= float(rng.uniform(0.72, 1.28))
        if len(speech) > 20_000:
            speech = speech[:20_000]
        start = int(rng.integers(1_600, CLIP_SAMPLES - len(speech) - 1_600))
        clip = np.zeros(CLIP_SAMPLES, dtype=np.float32)
        clip[start : start + len(speech)] = speech

        delay = int(rng.integers(320, 1_600))
        echo_gain = float(rng.uniform(0.0, 0.18))
        clip[delay:] += clip[:-delay] * echo_gain

        noise = np.resize(room_noise, CLIP_SAMPLES).copy()
        rng.shuffle(noise)
        speech_rms = max(float(np.sqrt(np.mean(speech**2))), 1e-4)
        noise_rms = max(float(np.sqrt(np.mean(noise**2))), 1e-4)
        snr = float(rng.uniform(14.0, 34.0))
        clip += noise * (speech_rms / (noise_rms * 10 ** (snr / 20)))
        clip += rng.normal(0.0, float(rng.uniform(0.0002, 0.002)), CLIP_SAMPLES)
        clips[index] = np.clip(clip * 32767.0, -32768, 32767).astype(np.int16)
    return clips


class WakeWordNet(torch.nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        self.flatten = torch.nn.Flatten()
        self.input = torch.nn.Linear(INPUT_SHAPE[0] * INPUT_SHAPE[1], width)
        self.input_norm = torch.nn.LayerNorm(width)
        self.hidden = torch.nn.Linear(width, width)
        self.hidden_norm = torch.nn.LayerNorm(width)
        self.output = torch.nn.Linear(width, 1)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        values = torch.relu(self.input_norm(self.input(self.flatten(values))))
        values = torch.relu(self.hidden_norm(self.hidden(values)))
        return torch.sigmoid(self.output(values))


def predictions(model: WakeWordNet, values: np.ndarray, device: torch.device) -> np.ndarray:
    with torch.no_grad():
        tensor = torch.from_numpy(np.array(values, dtype=np.float32, copy=True)).to(device)
        return model(tensor).squeeze(1).cpu().numpy()


def generic_windows(values: np.ndarray, starts: np.ndarray) -> np.ndarray:
    return np.stack([values[int(start) : int(start) + INPUT_SHAPE[0]] for start in starts])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice-wav", required=True, type=Path)
    parser.add_argument("--features-dir", required=True, type=Path)
    parser.add_argument("--validation-features", required=True, type=Path)
    parser.add_argument("--openwakeword-source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=3_000)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--negative-weight", type=float, default=8.0)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    rng = np.random.default_rng(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    utterances, room_noise = load_utterances(args.voice_wav)
    train_utterances = utterances[:-2]
    validation_utterances = utterances[-2:]
    train_clips = augmented_clips(train_utterances, room_noise, 1_600, args.seed)
    validation_clips = augmented_clips(validation_utterances, room_noise, 256, args.seed + 1)

    import sys

    sys.path.insert(0, str(args.openwakeword_source))
    from openwakeword.utils import AudioFeatures

    feature_models = args.openwakeword_source / "openwakeword/resources/models"
    extractor = AudioFeatures(
        melspec_model_path=str(feature_models / "melspectrogram.onnx"),
        embedding_model_path=str(feature_models / "embedding_model.onnx"),
        inference_framework="onnx",
        ncpu=args.threads,
    )
    personal_train = extractor.embed_clips(train_clips, batch_size=128, ncpu=args.threads)
    personal_validation = extractor.embed_clips(
        validation_clips, batch_size=128, ncpu=args.threads
    )
    if personal_train.shape[1:] != INPUT_SHAPE or personal_validation.shape[1:] != INPUT_SHAPE:
        raise RuntimeError(
            f"Unexpected personalized feature shapes: {personal_train.shape}, "
            f"{personal_validation.shape}"
        )
    np.save(args.output_dir / "personal-features-train.npy", personal_train)
    np.save(args.output_dir / "personal-features-validation.npy", personal_validation)

    synthetic_positive = np.load(
        args.features_dir / "positive_features_train.npy", mmap_mode="r"
    )
    synthetic_negative = np.load(
        args.features_dir / "negative_features_train.npy", mmap_mode="r"
    )
    validation_values = np.load(args.validation_features, mmap_mode="r")
    if synthetic_positive.shape[1:] != INPUT_SHAPE or synthetic_negative.shape[1:] != INPUT_SHAPE:
        raise RuntimeError("Synthetic features have the wrong shape")
    if validation_values.ndim != 2 or validation_values.shape[1] != INPUT_SHAPE[1]:
        raise RuntimeError("Generic negative features have the wrong shape")

    split = int(validation_values.shape[0] * 0.75)
    holdout_starts = np.arange(split, validation_values.shape[0] - INPUT_SHAPE[0], 16)
    holdout_starts = holdout_starts[:6_000]
    generic_holdout = generic_windows(validation_values, holdout_starts)
    synthetic_validation_positive = np.load(
        args.features_dir / "positive_features_test.npy", mmap_mode="r"
    )[:512]
    synthetic_validation_negative = np.load(
        args.features_dir / "negative_features_test.npy", mmap_mode="r"
    )[:512]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = WakeWordNet(args.width).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.steps)
    best_state = copy.deepcopy(model.state_dict())
    best_score: tuple[int, int, float, float] = (0, -10**9, -1.0, -1.0)
    history: list[dict[str, float | int]] = []

    for step in range(1, args.steps + 1):
        positive = np.concatenate(
            (
                personal_train[rng.integers(len(personal_train), size=32)],
                synthetic_positive[rng.integers(len(synthetic_positive), size=16)],
            )
        )
        negative = np.concatenate(
            (
                synthetic_negative[rng.integers(len(synthetic_negative), size=32)],
                generic_windows(
                    validation_values,
                    rng.integers(0, split - INPUT_SHAPE[0], size=96),
                ),
            )
        )
        values = np.concatenate((positive, negative)).astype(np.float32)
        labels = np.concatenate(
            (np.ones(len(positive), dtype=np.float32), np.zeros(len(negative), dtype=np.float32))
        )
        order = rng.permutation(len(labels))
        x = torch.from_numpy(values[order]).to(device)
        y = torch.from_numpy(labels[order, None]).to(device)
        negative_weight = 1.5 + (args.negative_weight - 1.5) * step / args.steps
        weight = torch.where(
            y == 0,
            torch.tensor(negative_weight, device=device),
            torch.tensor(1.0, device=device),
        )

        optimizer.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy(model(x), y, weight=weight)
        loss.backward()
        optimizer.step()
        scheduler.step()

        if step == 1 or step % 200 == 0 or step == args.steps:
            personal_scores = predictions(model, personal_validation, device)
            generic_scores = predictions(model, generic_holdout, device)
            positive_scores = predictions(model, synthetic_validation_positive, device)
            negative_scores = predictions(model, synthetic_validation_negative, device)
            personal_recall = float(np.mean(personal_scores >= PRODUCTION_THRESHOLD))
            generic_false_positives = int(np.sum(generic_scores >= PRODUCTION_THRESHOLD))
            synthetic_accuracy = float(
                (np.mean(positive_scores >= PRODUCTION_THRESHOLD)
                + np.mean(negative_scores < PRODUCTION_THRESHOLD))
                / 2
            )
            recall_floor_met = personal_recall >= 0.90
            score = (
                int(recall_floor_met),
                -generic_false_positives if recall_floor_met else -10**9,
                synthetic_accuracy,
                personal_recall,
            )
            history.append(
                {
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "personal_recall": personal_recall,
                    "generic_false_positives": generic_false_positives,
                    "synthetic_balanced_accuracy": synthetic_accuracy,
                }
            )
            print(json.dumps(history[-1], sort_keys=True), flush=True)
            if score > best_score:
                best_score = score
                best_state = copy.deepcopy(model.state_dict())

    model.load_state_dict(best_state)
    model = model.to("cpu").eval()
    onnx_path = args.output_dir / "gi-v5.onnx"
    torch.onnx.export(
        model,
        torch.zeros((1,) + INPUT_SHAPE, dtype=torch.float32),
        onnx_path,
        input_names=["x"],
        output_names=["gi"],
        opset_version=13,
    )
    report = {
        "schema_version": 1,
        "model": "gi-v5-personalized",
        "seed": args.seed,
        "steps": args.steps,
        "width": args.width,
        "maximum_negative_weight": args.negative_weight,
        "production_threshold": PRODUCTION_THRESHOLD,
        "voice_sha256": sha256(args.voice_wav),
        "utterance_count": len(utterances),
        "train_utterance_count": len(train_utterances),
        "validation_utterance_count": len(validation_utterances),
        "human_audio_used": True,
        "history": history,
        "onnx_sha256": sha256(onnx_path),
    }
    (args.output_dir / "gi-v5-training.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
