# GI openWakeWord model

The private `gi.tflite` model detects the two spoken letter names `gee eye`.
The Kubernetes service uses the filename stem `gi` as the Wyoming model ID.
The complete training parameters are in `gi-training.yaml`. The binary is not
committed to this public repository.

## Recorded inputs

| Input | Exact source | Pinned revision or checksum |
| --- | --- | --- |
| Public openWakeWord Colab notebook export | Drive export URL below | `05aa4ba6aa0c37042be2cd4bd32ce5b91d7357445769a563aa23a50cf0a3412c` |
| Modified notebook used for version 1 | pCloud `docs/soyspray/home-assistant-voice/gi-v1-modified-training.ipynb` | `b6828860088e327f805045453124845a54433c29efe9fae972fd82130e079829` |
| openWakeWord source | `https://github.com/dscripka/openWakeWord.git` | `368c03716d1e92591906a84949bc477f3a834455` |
| Piper sample generator | `https://github.com/rhasspy/piper-sample-generator.git` | `213d4d561ab8a84f71de7dddac827cb07e92c031` |
| Piper `en_US-libritts_r-medium.pt` checkpoint, 204,089,915 bytes | `https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/en_US-libritts_r-medium.pt` | `e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6` |
| AudioSet dataset | `https://huggingface.co/datasets/agkphysics/AudioSet` | `0c609e8302cf139307f639c57652032af0a88041` |
| openWakeWord feature dataset | `https://huggingface.co/datasets/davidscripka/openwakeword_features` | `985bf1b47e7f19c07741af82bfe32d5a9dc56096` |
| MIT environmental impulse responses | `https://huggingface.co/datasets/davidscripka/MIT_environmental_impulse_responses` | `b824a1ef2821f112fda0b9cb26e4278c62b425bb` |
| Private version 2 artifact bundle | pCloud `docs/soyspray/home-assistant-voice/gi-v2-private-artifacts.zip` | `82c084267f6d21a227d984503c240c0d04327f38ab62ef47facb5c95ea116ca2` |
| Private version 2 `gi.tflite`, 207,084 bytes | pCloud `docs/soyspray/home-assistant-voice/gi-v2.tflite` | `4b89c92d8500243404a77af30a7d8f8a618718403a355a3564e18108bc8f9739` |

The notebook export is available at:

```text
https://drive.google.com/uc?export=download&id=1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb
```

The laptop retrieves the private deployment artifact from the mounted pCloud
drive. This path is canonical for model version 2:

```bash
PCLOUD_DRIVE="${HOME}/pCloudDrive"
export VOICE_ASSISTANT_GI_MODEL_PATH="${PCLOUD_DRIVE}/docs/soyspray/home-assistant-voice/gi-v2.tflite"
test -f "${VOICE_ASSISTANT_GI_MODEL_PATH}"
echo '4b89c92d8500243404a77af30a7d8f8a618718403a355a3564e18108bc8f9739  '"${VOICE_ASSISTANT_GI_MODEL_PATH}" \
  | sha256sum --check --strict
```

The private bundle also contains the ONNX model and external data, the exact
runtime YAML, the patched `torch-audiomentations` source, a complete
`pip freeze --all` lock, and a JSON manifest with every internal file size
and SHA-256. Verify the bundle before recovery or retraining:

```bash
PCLOUD_DRIVE="${HOME}/pCloudDrive"
echo '82c084267f6d21a227d984503c240c0d04327f38ab62ef47facb5c95ea116ca2  '"${PCLOUD_DRIVE}/docs/soyspray/home-assistant-voice/gi-v2-private-artifacts.zip" \
  | sha256sum --check --strict
unzip -t "${PCLOUD_DRIVE}/docs/soyspray/home-assistant-voice/gi-v2-private-artifacts.zip"
```

Before the Piper compatibility patch loads its pickle-bearing checkpoint, run:

```bash
echo 'e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6  piper-sample-generator/models/en_US-libritts_r-medium.pt' \
  | sha256sum --check --strict
```

The run used 1,000 synthetic positive clips, 500 validation clips, 10,000
training steps, and a maximum negative weight of 1,500. Background data was
the first 300 rows from the pinned AudioSet balanced split, converted to 16 kHz WAV.
The FMA dataset was not used. The pinned ACAV100M and false-positive feature
arrays were used directly.

## Colab compatibility record

The public notebook was not directly runnable on the 2026-08 Colab runtime.
The recorded run made these fail-closed compatibility changes:

1. Use NumPy `2.0.2` and `datasets` `4.0.0`.
2. Check out the source revisions in the table before training.
3. Require the exact Piper checkpoint size and SHA-256 in the table before
   loading it. For that verified file only, call
   `torch.load(..., weights_only=False)`. PyTorch changed this default after
   the notebook was published. This file is pickle-bearing; do not bypass the
   checksum for a replacement download.
4. Guard the removed `torchaudio.set_audio_backend("soundfile")` call with
   `hasattr` in `torch-audiomentations` `0.11.0`. Replace its removed
   `torchaudio.info` and `torchaudio.load` calls with SoundFile metadata and
   `float32`, two-dimensional reads, then transpose the result back to
   channel-first tensors.
5. Replace the removed AudioSet tar URL with the pinned Hugging Face balanced
   parquet split and take 300 clips.
6. Download both precomputed feature arrays from the pinned feature-dataset
   revision. Do not use its mutable `main` URLs.
7. Use only `./audioset_16k` as `background_paths` and run the three training
   stages from `gi-training.yaml`: `--generate_clips`, `--augment_clips`, then
   `--train_model`.
8. The pinned training script defines `--convert_to_tflite` with the string
   default `"False"`, which is truthy. It exports the ONNX model, then its old
   converter exits non-zero. The ONNX input is named `x` and has shape
   `1x16x96`. Preserve that non-image input and fail the conversion when the
   32 seeded ONNX/TFLite comparisons exceed the converter thresholds:

   ```bash
   onnx2tf -i gi-v2.onnx -o gi-v2-conversion -kat x -ewo -efot -ens 32
   ```

   Promote `gi-v2-conversion/gi-v2_float32.tflite` as `gi-v2.tflite`.
   Version 1 used a nonexistent input name with `-kat`. onnx2tf ignored it and
   transposed the input to `1x96x16`. The startup probe rejected that model
   before the Wyoming service became ready. Keep version 1 only as an audit
   artifact; do not deploy it.

The notebook warns that its mixed training inputs have different licenses and
usage restrictions. Treat this model as non-commercial personal-use material.
Do not publish or sell it without a separate source-by-source license review.

Clip generation and augmentation are stochastic. A documented rerun is
functionally reproducible, but it is not expected to produce identical model
bytes. The private `gi.tflite` file and its Git-pinned checksum are the
deployment source of truth.

## Version 3 candidate

Version 2 used only 1,000 training examples and is not reliable across six
short human samples. The finite Wyoming file test detected none. A quiet
speaker-to-Voice-PE test detected two of six isolated attempts at the same
playback level. Keep the original recording and these six attempts as
regression evidence. Do not use them for training or checkpoint selection.

The candidate configuration is `gi-v3-training.yaml`. It uses 20,000 synthetic
positive clips, 2,000 synthetic validation clips, and 50,000 training steps.
Keep the version 2 background sources, feature arrays, Piper voice, and pinned
source revisions unchanged for the first candidate. Use a free Colab GPU. Do
not select a paid runtime without separate approval.

Do not upload the human recordings to Colab. Build the first candidate only
from the recorded public synthetic inputs. Keep all human recordings private
and held out. Seal the held-out set before candidate
scoring. It must contain at least five target utterances plus confusing speech,
room noise, television, and music negatives. Put only aggregate counts and
checksums in Git.

Convert the frozen ONNX candidate outside the training environment with the
pinned version 3 conversion lock and `-kat x -ewo -efot -ens 32`. Promote
version 3 only if it passes all held-out positives, rejects all held-out
negatives, passes the Wyoming positive and negative smoke tests, and activates
reliably through the real Voice PE. Keep version 2 available for rollback.

## Promotion checks

The private model is promoted only when all of these checks pass:

- The pinned openWakeWord runtime can load it and execute one zero-feature
  inference window.
- The conversion compares 32 seeded ONNX and TFLite outputs. The recorded
  maximum absolute error is `3.5762786865234375e-07`.
- Piper synthesis of `gee eye` returns a `gi` Wyoming detection.
- Synthesized `okay nabu`, `hey jarvis`, `hey mycroft`, a normal light command,
  `gee`, and `eye` all return `NotDetected`.
- A human voice activates the Voice PE with `GI` and does not activate it with
  `Okay Nabu`.

The first model is intentionally small. If household speech, television, or
music produces false wakes, add those recordings as held-out negatives and
train a new version. Do not lower the runtime threshold before measuring the
false-wake rate.
