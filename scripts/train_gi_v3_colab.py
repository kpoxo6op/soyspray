#!/usr/bin/env python3
"""Build the synthetic-only GI v3 wake-word candidate on free Colab CUDA."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import NamedTuple, Sequence

DRIVER = Path(__file__).resolve()
ROOT = DRIVER.parents[1]
TRAINING_LOCK = ROOT / "scripts/gi-v3-training.lock"
CONVERSION_LOCK = ROOT / "scripts/gi-v3-conversion.lock"
TRAINING_LOCK_SHA256 = "579f06f6ad5b398fb65a6217070a3e860cb7d483f5e4f62f4273211cdbe54ba3"
CONVERSION_LOCK_SHA256 = "09a54fc0a2a681f70afae40dfbeb7e32fdc2158c808a0f376446719ffc1d75fc"
LOCK_PROVENANCE = {
    "training": {
        "file": TRAINING_LOCK.name,
        "sha256": TRAINING_LOCK_SHA256,
        "target": "CPython 3.12.13 x86_64-manylinux_2_28",
    },
    "conversion": {
        "file": CONVERSION_LOCK.name,
        "sha256": CONVERSION_LOCK_SHA256,
        "target": "CPython 3.12.13 x86_64-manylinux_2_35",
    },
}
DEFAULT_CONFIG = (
    ROOT
    / "playbooks/argocd/applications/home-automation/voice-assistant/models"
    / "gi-v3-training.yaml"
)
CONFIG_SHA256 = "411d067731a7bbb6e1e1c61c36e9387f3e5f59fefa65abfe8a97b224ee28ec04"

REVISIONS = {
    "openwakeword": "368c03716d1e92591906a84949bc477f3a834455",
    "piper": "213d4d561ab8a84f71de7dddac827cb07e92c031",
    "audioset": "0c609e8302cf139307f639c57652032af0a88041",
    "features": "985bf1b47e7f19c07741af82bfe32d5a9dc56096",
    "rir": "b824a1ef2821f112fda0b9cb26e4278c62b425bb",
}

TRAIN_SOURCE_SHA256 = "8d559e4c1bc9b5523bae50e7ec8f642756a63a7bb5f323620d069a2d03db2972"
TRAIN_PATCHED_SHA256 = "5894e748b57dfa587cfd7517a7ee4bfccda87f8dea2e2546fea1b37b6fcc22bc"
PIPER_SOURCE_SHA256 = "c16312476b7abc60597d03508568253ed2f225e4b915e0e8569569dd2d956cc2"
PIPER_PATCHED_SHA256 = "cfdc3df17e8aef0688eb3d8ee685573d0fb32f0bc83f85299b5fc6721918a1d6"
AUDIO_IO_SOURCE_SHA256 = "f5cb444766189d29ebbb02f446df7a37b9a7e40aed73c8dafdaaae23652bd6d1"
AUDIO_IO_PATCHED_SHA256 = "4e66a974bb99956cee81b826c3e83e259159948e82562f259026dc06cc70ffa1"
OWW_SETUP_SOURCE_SHA256 = "6487c132db5a16b1b45964321bac15cc3d87e23d3bd98edc2f89990a4072a2af"
OWW_SETUP_PATCHED_SHA256 = "8816856e0396bf62460860fe2bd40d0f26d09ece6b1196a5a8e9d6602ca1ac49"


class Download(NamedTuple):
    url: str
    filename: str
    size: int
    sha256: str


def _release(name: str, size: int, sha256: str) -> Download:
    return Download(
        f"https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{name}",
        name,
        size,
        sha256,
    )


DOWNLOADS = {
    "pip": Download(
        "https://files.pythonhosted.org/packages/b7/3f/"
        "945ef7ab14dc4f9d7f40288d2df998d1837ee0888ec3659c813487572faa/"
        "pip-25.2-py3-none-any.whl",
        "pip-25.2-py3-none-any.whl",
        1_752_557,
        "6d67a2b4e7f14d8b31b8b52648866fa717f45a1eb70e83002f4331d07e953717",
    ),
    "setuptools": Download(
        "https://files.pythonhosted.org/packages/94/b8/"
        "f1f62a5e3c0ad2ff1d189590bfa4c46b4f3b6e49cef6f26c6ee4e575394d/"
        "setuptools-80.10.2-py3-none-any.whl",
        "setuptools-80.10.2-py3-none-any.whl",
        1_064_234,
        "95b30ddfb717250edb492926c92b5221f7ef3fbcc2b07579bcd4a27da21d0173",
    ),
    "flit_core": Download(
        "https://files.pythonhosted.org/packages/f2/65/"
        "b6ba90634c984a4fcc02c7e3afe523fef500c4980fec67cc27536ee50acf/"
        "flit_core-3.12.0-py3-none-any.whl",
        "flit_core-3.12.0-py3-none-any.whl",
        45_594,
        "e7a0304069ea895172e3c7bb703292e992c5d1555dd1233ab7b5621b5b69e62c",
    ),
    "wheel": Download(
        "https://files.pythonhosted.org/packages/0b/2c/"
        "87f3254fd8ffd29e4c02732eee68a83a1d3c346ae39bc6822dcbcb697f2b/"
        "wheel-0.45.1-py3-none-any.whl",
        "wheel-0.45.1-py3-none-any.whl",
        72_494,
        "708e7481cc80179af0e556bbf0cc00b8444c7321e2700b8d8580231d13017248",
    ),
    "acoustics_sdist": Download(
        "https://files.pythonhosted.org/packages/28/55/"
        "6039f24c69f2c3fcdb9ca1655a28fe9bd66a698479fc12e79e8dcd9efd1f/"
        "acoustics-0.2.6.tar.gz",
        "acoustics-0.2.6.tar.gz",
        3_476_036,
        "d02bcc84251cfa2edd3e21c7f885dd963f8e8c587f975c2f9d4e1d9b142bcc52",
    ),
    "pronouncing_sdist": Download(
        "https://files.pythonhosted.org/packages/7f/c6/"
        "9dc74a3ddca71c492e224116b6654592bfe5717b4a78582e4d9c3345d153/"
        "pronouncing-0.2.0.tar.gz",
        "pronouncing-0.2.0.tar.gz",
        17_562,
        "ff7856e1d973b3e16ff490c5cf1abdb52f08f45e2c35e463249b75741331e7c4",
    ),
    "deep_phonemizer_sdist": Download(
        "https://files.pythonhosted.org/packages/6f/39/"
        "f04c12980b6d639247b7d544abcd5b5e2727ee2b9c5f2e01e8a0bf735041/"
        "deep-phonemizer-0.0.19.tar.gz",
        "deep-phonemizer-0.0.19.tar.gz",
        29_731,
        "6f47af558f0a51eec20080fc2dce999010d9342586ad42350496da0ba1610ec3",
    ),
    "speexdsp_ns": Download(
        "https://files.pythonhosted.org/packages/7b/14/"
        "d9fd843472f82853643c4ae09835c76bfb19ce7e712586cfc1318030503f/"
        "speexdsp_ns-0.1.2-cp312-cp312-manylinux_2_28_x86_64.whl",
        "speexdsp_ns-0.1.2-cp312-cp312-manylinux_2_28_x86_64.whl",
        161_569,
        "c2c73c2f132212fecfff52a689594f925453ff521fec336411149256aedcd819",
    ),
    "piper_checkpoint": Download(
        "https://github.com/rhasspy/piper-sample-generator/releases/download/"
        "v2.0.0/en_US-libritts_r-medium.pt",
        "en_US-libritts_r-medium.pt",
        204_089_915,
        "e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6",
    ),
    "embedding_onnx": _release(
        "embedding_model.onnx",
        1_326_578,
        "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",
    ),
    "embedding_tflite": _release(
        "embedding_model.tflite",
        1_330_312,
        "c0aea21eb84a4ce90a08c870da41b7a7173b45269e6a3207c71d67c40f3a59d8",
    ),
    "melspectrogram_onnx": _release(
        "melspectrogram.onnx",
        1_087_958,
        "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",
    ),
    "melspectrogram_tflite": _release(
        "melspectrogram.tflite",
        1_092_516,
        "96fa0adccb6e8cf95cb14465409a1a2898ee4a96a85bb9ed3c7eb0e68bf163e8",
    ),
    "audioset": Download(
        "https://huggingface.co/datasets/agkphysics/AudioSet/resolve/"
        f"{REVISIONS['audioset']}/data/bal_train/00.parquet?download=true",
        "audioset-balanced-00.parquet",
        687_636_067,
        "b433e7bcf3bbdfb0488791fceae1eb7100711d13093d22e2253f15d2dcabc084",
    ),
    "acav_features": Download(
        "https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/"
        f"{REVISIONS['features']}/openwakeword_features_ACAV100M_2000_hrs_16bit.npy?download=true",
        "openwakeword_features_ACAV100M_2000_hrs_16bit.npy",
        17_280_000_128,
        "721a66d0682c65a1b5c1da0aa109409cede1d20e28b15235c344b000cbb7654f",
    ),
    "validation_features": Download(
        "https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/"
        f"{REVISIONS['features']}/validation_set_features.npy?download=true",
        "validation_set_features.npy",
        184_836_608,
        "a56a8a0f8e0efb91900acc6de4c0cdf4c564842e8475a7d49b36c039e17a690f",
    ),
    "torch": Download(
        "https://download.pytorch.org/whl/cu121/torch-2.5.0%2Bcu121-cp312-cp312-linux_x86_64.whl",
        "torch-2.5.0+cu121-cp312-cp312-linux_x86_64.whl",
        780_367_618,
        "c4e0eb78c24d6991db93d86f06809edb10ac15220363b04ef18e22da50f059fe",
    ),
    "torchvision": Download(
        "https://download.pytorch.org/whl/cu121/"
        "torchvision-0.20.0%2Bcu121-cp312-cp312-linux_x86_64.whl",
        "torchvision-0.20.0+cu121-cp312-cp312-linux_x86_64.whl",
        7_283_863,
        "e794f7728dd5cec0d9bfa12749019d072a841e8dc2cdc1aba09afc63c5bb7ec3",
    ),
    "torchaudio": Download(
        "https://download.pytorch.org/whl/cu121/"
        "torchaudio-2.5.0%2Bcu121-cp312-cp312-linux_x86_64.whl",
        "torchaudio-2.5.0+cu121-cp312-cp312-linux_x86_64.whl",
        3_413_081,
        "6f06233a9e32b1997ebd1b9736321cd88e6f156aeef225529ac31dc5bb056024",
    ),
    "piper_phonemize": Download(
        "https://files.pythonhosted.org/packages/76/3f/"
        "f3d1e2d5ef7005abf6f7812d06b471788346dda2b82de285ae87ab45a9fa/"
        "piper_phonemize_cross-1.2.1-cp312-cp312-manylinux_2_28_x86_64.whl",
        "piper_phonemize_cross-1.2.1-cp312-cp312-manylinux_2_28_x86_64.whl",
        15_575_585,
        "f171d5bd5a7e19871c9ef6b5a21390020587034ad140bc678d9360bc1627df1d",
    ),
    "onnxruntime_gpu": Download(
        "https://files.pythonhosted.org/packages/ed/cd/"
        "98ea1ef90c5e51de69239881522a4c115a009dba99d83fd8e2606b33358d/"
        "onnxruntime_gpu-1.20.0-cp312-cp312-manylinux_2_27_x86_64."
        "manylinux_2_28_x86_64.whl",
        "onnxruntime_gpu-1.20.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
        291_507_294,
        "06398420c363b7e400de98deb8bc238fcff98adafe8eeda6ff96a94e20713ac0",
    ),
}

TRAIN_REQUIREMENTS = (
    "setuptools==80.10.2",
    "flit-core==3.12.0",
    "wheel==0.45.1",
    "numpy==2.0.2",
    "datasets==4.0.0",
    "mutagen==1.47.0",
    "torchinfo==1.8.0",
    "torchmetrics==1.2.0",
    "speechbrain==0.5.14",
    "audiomentations==0.33.0",
    "torch-audiomentations==0.11.0",
    "acoustics==0.2.6",
    "pronouncing==0.2.0",
    "deep-phonemizer==0.0.19",
    "webrtcvad-wheels==2.0.14",
    "onnx==1.19.1",
    "ai-edge-litert==2.1.2",
    "librosa==0.10.2.post1",
    "soundfile==0.14.0",
    "scipy==1.16.3",
    "PyYAML==6.0.3",
    "pyarrow==18.1.0",
    "numba==0.60.0",
    "llvmlite==0.43.0",
    "protobuf==7.35.1",
    "scikit-learn==1.6.1",
    "speexdsp-ns==0.1.2",
    "tqdm==4.67.1",
)

CONVERSION_REQUIREMENTS = (
    "onnx2tf==2.6.8",
    "ai-edge-litert==2.1.2",
    "numpy==2.2.6",
    "onnx==1.20.1",
    "onnxruntime==1.26.0",
    "onnxsim==0.6.5",
    "onnxoptimizer==0.4.2",
    "onnx-graphsurgeon==0.6.1",
    "sne4onnx==2.0.1",
    "sng4onnx==2.0.1",
    "h5py==3.14.0",
    "protobuf==7.35.1",
    "pyopen-wakeword==1.1.0",
    "tensorflow==2.21.0",
    "tf-keras==2.21.0",
    "keras==3.15.0",
)

CONVERSION_REPORTS = (
    "gi_accuracy_report.json",
    "gi_accuracy_comparison_report.json",
)

AUDIOSET_EXTRACTOR = r"""
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from datasets import Audio, load_dataset
from scipy.signal import resample_poly

source, output = Path(sys.argv[1]), Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=True)
dataset = load_dataset(
    "parquet", data_files={"train": str(source)}, split="train", streaming=True
).cast_column("audio", Audio(decode=False))
rows = iter(dataset)
files = []
for index in range(300):
    try:
        encoded = next(rows)["audio"]["bytes"]
    except StopIteration as error:
        raise RuntimeError("AudioSet shard has fewer than 300 rows") from error
    if not isinstance(encoded, bytes) or not encoded:
        raise RuntimeError(f"AudioSet row {index} has no embedded audio bytes")
    samples, sample_rate = sf.read(io.BytesIO(encoded), dtype="float32", always_2d=True)
    mono = samples.mean(axis=1)
    if sample_rate != 16000:
        divisor = math.gcd(sample_rate, 16000)
        mono = resample_poly(mono, 16000 // divisor, sample_rate // divisor)
    path = output / f"{index:04d}.wav"
    sf.write(path, np.clip(mono, -1.0, 1.0), 16000, subtype="PCM_16")
    files.append({
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
manifest = {
    "source": source.name,
    "source_bytes": source.stat().st_size,
    "source_sha256": "b433e7bcf3bbdfb0488791fceae1eb7100711d13093d22e2253f15d2dcabc084",
    "rows": 300,
    "files": files,
}
(output / "audioset-manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n"
)
""".strip()

PARITY_VERIFIER = r"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from ai_edge_litert.interpreter import Interpreter
from pyopen_wakeword import OpenWakeWord

onnx_path, tflite_path, report_path = map(Path, sys.argv[1:4])
session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
onnx_input = session.get_inputs()[0]
if onnx_input.name != "x" or list(onnx_input.shape) != [1, 16, 96]:
    raise RuntimeError(f"Bad ONNX input: {onnx_input.name} {onnx_input.shape}")
interpreter = Interpreter(model_path=str(tflite_path))
interpreter.allocate_tensors()
tflite_input = interpreter.get_input_details()[0]
tflite_output = interpreter.get_output_details()[0]
if list(tflite_input["shape"]) != [1, 16, 96]:
    raise RuntimeError(f"Bad TFLite input: {tflite_input['shape']}")
rng = np.random.default_rng(0)
onnx_values, tflite_values = [], []
for _ in range(32):
    sample = rng.standard_normal((1, 16, 96), dtype=np.float32)
    onnx_values.append(session.run(None, {"x": sample})[0].ravel())
    interpreter.set_tensor(tflite_input["index"], sample)
    interpreter.invoke()
    tflite_values.append(interpreter.get_tensor(tflite_output["index"]).ravel())
left, right = np.concatenate(onnx_values), np.concatenate(tflite_values)
maximum = float(np.max(np.abs(left - right)))
cosine = float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))
if not np.isfinite(maximum) or not np.isfinite(cosine) or maximum > 1e-5 or cosine < 0.99999:
    raise RuntimeError(f"ONNX/TFLite parity failed: max_abs={maximum}, cosine={cosine}")
wake_word = OpenWakeWord.from_model(tflite_path)
try:
    if wake_word.input_windows != 16:
        raise RuntimeError(f"Pinned runtime reports {wake_word.input_windows} input windows")
    one_window = np.zeros((1, 1, 1, 96), dtype=np.float32)
    for _ in range(15):
        if list(wake_word.process_streaming(one_window)):
            raise RuntimeError("Pinned runtime returned output before window 16")
    streaming_output = list(wake_word.process_streaming(one_window))
    if len(streaming_output) != 1:
        raise RuntimeError(f"Pinned runtime returned {len(streaming_output)} outputs at window 16")
finally:
    wake_word.close()
report_path.write_text(json.dumps({
    "input_name": "x", "input_shape": [1, 16, 96], "seed": 0,
    "seeded_samples": 32, "max_absolute_error": maximum,
    "cosine_similarity": cosine, "pyopen_wakeword": "1.1.0",
    "streaming_first_output_window": 16,
}, indent=2, sort_keys=True) + "\n")
""".strip()


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{path}.part")
    temporary.write_text(text)
    os.replace(temporary, path)


def verify_file(path: Path, asset: Download) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing pinned input: {path}")
    if path.stat().st_size != asset.size:
        raise RuntimeError(f"Wrong byte count for {path}: {path.stat().st_size}")
    actual = sha256(path)
    if actual != asset.sha256:
        raise RuntimeError(f"Wrong SHA-256 for {path}: {actual}")


def download_command(asset: Download, destination: Path) -> tuple[list[str], Path]:
    part = Path(f"{destination}.part")
    return (
        [
            "curl",
            "--fail",
            "--location",
            "--continue-at",
            "-",
            "--retry",
            "5",
            "--retry-all-errors",
            asset.url,
            "--output",
            str(part),
        ],
        part,
    )


def download(asset: Download, destination: Path) -> None:
    if destination.exists():
        verify_file(destination, asset)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    command, part = download_command(asset, destination)
    if part.exists() and part.stat().st_size > asset.size:
        raise RuntimeError(f"Partial download is larger than the pinned input: {part}")
    if part.exists() and part.stat().st_size == asset.size:
        verify_file(part, asset)
        os.replace(part, destination)
        return
    subprocess.run(command, check=True)
    verify_file(part, asset)
    os.replace(part, destination)


def _patch(
    path: Path,
    source_sha256: str,
    patched_sha256: str,
    replacements: Sequence[tuple[str, str, int]],
) -> None:
    actual = sha256(path)
    if actual == patched_sha256:
        return
    if actual != source_sha256:
        raise RuntimeError(f"Unexpected source SHA-256 for {path}: {actual}")
    text = path.read_text()
    for old, new, count in replacements:
        if text.count(old) != count:
            raise RuntimeError(f"Expected {count} exact patch targets in {path}")
        text = text.replace(old, new)
    atomic_text(path, text)
    actual = sha256(path)
    if actual != patched_sha256:
        raise RuntimeError(f"Unexpected patched SHA-256 for {path}: {actual}")


def patch_train(path: Path) -> None:
    accuracy = '                    self.best_val_accuracy = self.history["val_accuracy"][-1]\n'
    _patch(
        path,
        TRAIN_SOURCE_SHA256,
        TRAIN_PATCHED_SHA256,
        (
            ('default="False",', "default=False,", 5),
            (
                '            adversarial_texts = config["custom_negative_phrases"]',
                '            adversarial_texts = list(config["custom_negative_phrases"])',
                2,
            ),
            (
                '        if n_current_samples <= 0.95*config["n_samples"]:',
                '        if n_current_samples < config["n_samples"]:',
                2,
            ),
            (
                '        if n_current_samples <= 0.95*config["n_samples_val"]:',
                '        if n_current_samples < config["n_samples_val"]:',
                2,
            ),
            (
                '                          os.path.join(output_dir, model_name + ".onnx"), opset_version=13)',
                '                          os.path.join(output_dir, model_name + ".onnx"), opset_version=13, input_names=["x"])',
                1,
            ),
            (
                "                             output_dir=positive_test_output_dir, auto_reduce_batch_size=True)",
                "                             output_dir=positive_test_output_dir, auto_reduce_batch_size=True,\n"
                '                             file_names=[uuid.uuid4().hex + ".wav" for i in range(config["n_samples_val"])])',
                1,
            ),
            (
                "                             output_dir=negative_test_output_dir, auto_reduce_batch_size=True)",
                "                             output_dir=negative_test_output_dir, auto_reduce_batch_size=True,\n"
                '                             file_names=[uuid.uuid4().hex + ".wav" for i in range(config["n_samples_val"])])',
                1,
            ),
            (
                accuracy,
                accuracy
                + '                    self.best_val_fp = min(self.best_val_fp, self.history["val_fp_per_hr"][-1])\n',
                1,
            ),
        ),
    )


def patch_openwakeword_setup(path: Path) -> None:
    _patch(
        path,
        OWW_SETUP_SOURCE_SHA256,
        OWW_SETUP_PATCHED_SHA256,
        (("'onnxruntime>=1.10.0,<2',", "'onnxruntime-gpu==1.20.0',", 1),),
    )


def patch_piper(path: Path) -> None:
    _patch(
        path,
        PIPER_SOURCE_SHA256,
        PIPER_PATCHED_SHA256,
        (
            (
                "torch_model = torch.load(model_path)",
                "torch_model = torch.load(model_path, weights_only=False)",
                1,
            ),
        ),
    )


def patch_audio_io(path: Path) -> None:
    metadata = """        info = torchaudio.info(file_path)
        # Deal with backwards-incompatible signature change.
        # See https://github.com/pytorch/audio/issues/903 for more information.
        if type(info) is tuple:
            si, ei = info
            num_samples = si.length
            sample_rate = si.rate
        else:
            num_samples = info.num_frames
            sample_rate = info.sample_rate
        return num_samples, sample_rate
"""
    loader = """                original_data, _ = torchaudio.load(
                    audio_path,
                    frame_offset=original_sample_offset,
                    num_frames=original_num_samples,
                )
"""
    _patch(
        path,
        AUDIO_IO_SOURCE_SHA256,
        AUDIO_IO_PATCHED_SHA256,
        (
            (
                "import librosa\nimport torch\n",
                "import librosa\nimport soundfile as sf\nimport torch\n",
                1,
            ),
            (
                'torchaudio.set_audio_backend("soundfile")\n',
                'if hasattr(torchaudio, "set_audio_backend"):\n    torchaudio.set_audio_backend("soundfile")\n',
                1,
            ),
            (
                metadata,
                "        info = sf.info(str(file_path))\n        return info.frames, info.samplerate\n",
                1,
            ),
            (
                loader,
                """                original_data, _ = sf.read(
                    audio_path,
                    start=original_sample_offset,
                    frames=original_num_samples,
                    always_2d=True,
                    dtype="float32",
                )
                original_data = torch.from_numpy(original_data.T.copy())
""",
                1,
            ),
        ),
    )


def run(command: Sequence[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def require_host_runtime() -> None:
    if sys.version_info[:3] != (3, 12, 13):
        raise RuntimeError(f"GI v3 requires Python 3.12.13, not {sys.version.split()[0]}")
    if shutil.which("nvidia-smi") is None:
        raise RuntimeError("GI v3 requires a CUDA GPU; select a free Colab GPU runtime")
    run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])


TRAIN_CUDA_PROBE = (
    "import onnxruntime as ort, torch; "
    "assert torch.cuda.is_available(), 'CUDA unavailable in PyTorch'; "
    "assert torch.version.cuda == '12.1', torch.version.cuda; "
    "assert 'CUDAExecutionProvider' in ort.get_available_providers(), ort.get_available_providers(); "
    "print(torch.cuda.get_device_name(0))"
)


def require_training_cuda(python: Path) -> None:
    run([str(python), "-c", TRAIN_CUDA_PROBE])


def require_free_disk(workspace: Path) -> None:
    probe = workspace.resolve()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    minimum = 35 * 1024**3
    available = shutil.disk_usage(probe).free
    if available < minimum:
        raise RuntimeError(
            f"GI v3 needs at least 35 GiB free in the workspace filesystem; found {available / 1024**3:.1f} GiB"
        )


def require_checkpoint_storage(
    checkpoint_dir: Path,
    *,
    content_root: Path = Path("/content"),
    is_mount=os.path.ismount,
) -> None:
    if not content_root.is_dir():
        return
    drive = content_root / "drive"
    mydrive = drive / "MyDrive"
    if not is_mount(drive) or not mydrive.is_dir():
        raise RuntimeError(
            "Mount Google Drive before training; /content/drive is not a mounted Google Drive"
        )
    try:
        checkpoint_dir.resolve().relative_to(mydrive.resolve())
    except ValueError as error:
        raise RuntimeError(
            "On Colab, --checkpoint-dir must be below /content/drive/MyDrive"
        ) from error


def clone_pinned(url: str, revision: str, destination: Path, lfs: bool = False) -> None:
    environment = os.environ.copy()
    if lfs:
        environment["GIT_LFS_SKIP_SMUDGE"] = "1"
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(
            ["git", "clone", "--no-checkout", "--filter=blob:none", url, str(destination)],
            env=environment,
        )
    if not (destination / ".git").is_dir():
        raise RuntimeError(f"Not a Git source directory: {destination}")
    run(["git", "fetch", "--depth", "1", "origin", revision], cwd=destination, env=environment)
    run(["git", "checkout", "--detach", revision], cwd=destination, env=environment)
    actual = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=destination, check=True, text=True, capture_output=True
    ).stdout.strip()
    if actual != revision:
        raise RuntimeError(f"Wrong revision for {destination}: {actual}")


def verify_patched_checkout(
    repository: Path,
    allowed: dict[Path, str],
    expected_revision: str | None = None,
) -> None:
    if expected_revision is not None:
        actual_revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        if actual_revision != expected_revision:
            raise RuntimeError(f"Wrong source revision for {repository}: {actual_revision}")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    allowed_names = {str(path): expected for path, expected in allowed.items()}
    for line in status:
        if len(line) < 4 or line[:2] not in {" M", "??"} or line[3:] not in allowed_names:
            raise RuntimeError(f"Unexpected dirty source checkout entry in {repository}: {line}")
    for name, expected in allowed_names.items():
        path = repository / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"Unexpected patched source in {repository}: {name}")


def _openwakeword_allowed_files() -> dict[Path, str]:
    allowed = {
        Path("openwakeword/train.py"): TRAIN_PATCHED_SHA256,
        Path("setup.py"): OWW_SETUP_PATCHED_SHA256,
    }
    for name in (
        "embedding_onnx",
        "embedding_tflite",
        "melspectrogram_onnx",
        "melspectrogram_tflite",
    ):
        asset = DOWNLOADS[name]
        allowed[Path("openwakeword/resources/models") / asset.filename] = asset.sha256
    return allowed


def verify_rir_checkout(repository: Path) -> None:
    actual_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if actual_revision != REVISIONS["rir"]:
        raise RuntimeError(f"Wrong RIR source revision: {actual_revision}")
    run(["git", "lfs", "fsck"], cwd=repository)
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(f"RIR working tree is dirty: {status}")
    run(["git", "diff", "--exit-code"], cwd=repository)
    count = len(list((repository / "16khz").glob("*.wav")))
    if count != 271:
        raise RuntimeError(f"Expected 271 pinned RIR WAV files, found {count}")


def verify_audioset_extract(output: Path) -> None:
    manifest_path = output / "audioset-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Missing AudioSet manifest: {manifest_path}")
    record = json.loads(manifest_path.read_text())
    files = record.get("files")
    if (
        record.get("source") != DOWNLOADS["audioset"].filename
        or record.get("source_bytes") != DOWNLOADS["audioset"].size
        or record.get("source_sha256") != DOWNLOADS["audioset"].sha256
        or record.get("rows") != 300
        or not isinstance(files, list)
        or len(files) != 300
    ):
        raise RuntimeError("AudioSet extract manifest has unexpected provenance or row count")
    expected_names = {f"{index:04d}.wav" for index in range(300)}
    if {path.name for path in output.glob("*.wav")} != expected_names:
        raise RuntimeError("AudioSet WAV set does not match the first 300 rows")
    for index, item in enumerate(files):
        name = f"{index:04d}.wav"
        path = output / name
        if (
            not isinstance(item, dict)
            or item.get("file") != name
            or item.get("bytes") != path.stat().st_size
            or item.get("sha256") != sha256(path)
        ):
            raise RuntimeError(f"AudioSet WAV failed verification: {name}")


def _python(venv: Path) -> Path:
    return venv / "bin/python"


def _create_venv(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError(
                f"Refusing to replace an unexpected virtual environment path: {path}"
            )
        shutil.rmtree(path)
    run([sys.executable, "-m", "venv", "--without-pip", str(path)])


def _pip(python: Path, *arguments: str) -> None:
    run([str(python), "-m", "pip", *arguments])


def _verify_lock(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing checked-in dependency lock: {path}")
    actual = sha256(path)
    if actual != expected_sha256:
        raise RuntimeError(
            f"Unexpected dependency lock SHA-256 for {path}: {actual}; expected {expected_sha256}"
        )


def _install_lock(python: Path, path: Path, expected_sha256: str) -> None:
    _verify_lock(path, expected_sha256)
    _pip(python, "install", "--require-hashes", "--only-binary=:all:", "-r", str(path))


def _bootstrap_pip(python: Path, wheel: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(wheel)
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            str(wheel),
        ],
        env=environment,
    )
    run(
        [
            str(python),
            "-c",
            "import pip; assert pip.__version__ == '25.2', pip.__version__",
        ]
    )


def _download_dependencies(downloads_dir: Path, names: Sequence[str]) -> dict[str, Path]:
    paths = {}
    for name in names:
        asset = DOWNLOADS[name]
        path = downloads_dir / asset.filename
        download(asset, path)
        paths[name] = path
    return paths


def _install_training_dependencies(python: Path, downloads_dir: Path) -> None:
    _verify_lock(TRAINING_LOCK, TRAINING_LOCK_SHA256)
    names = (
        "pip",
        "setuptools",
        "flit_core",
        "wheel",
        "torch",
        "torchvision",
        "torchaudio",
        "piper_phonemize",
        "onnxruntime_gpu",
        "speexdsp_ns",
        "acoustics_sdist",
        "pronouncing_sdist",
        "deep_phonemizer_sdist",
    )
    paths = _download_dependencies(downloads_dir, names)
    _bootstrap_pip(python, paths["pip"])
    _pip(
        python,
        "install",
        "--no-index",
        "--no-deps",
        *(str(paths[name]) for name in ("setuptools", "flit_core", "wheel")),
    )
    _pip(
        python,
        "install",
        "--no-index",
        "--no-deps",
        *(
            str(paths[name])
            for name in (
                "torch",
                "torchvision",
                "torchaudio",
                "piper_phonemize",
                "onnxruntime_gpu",
                "speexdsp_ns",
            )
        ),
    )
    _install_lock(python, TRAINING_LOCK, TRAINING_LOCK_SHA256)
    for name in ("acoustics_sdist", "pronouncing_sdist", "deep_phonemizer_sdist"):
        _pip(
            python,
            "install",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            str(paths[name]),
        )
    _pip(python, "check")


def _install_conversion_dependencies(python: Path, downloads_dir: Path) -> None:
    _verify_lock(CONVERSION_LOCK, CONVERSION_LOCK_SHA256)
    paths = _download_dependencies(downloads_dir, ("pip",))
    _bootstrap_pip(python, paths["pip"])
    _install_lock(python, CONVERSION_LOCK, CONVERSION_LOCK_SHA256)


def _probe_conversion_stack(python: Path) -> None:
    probe = (
        "from importlib.metadata import version; "
        "import onnx2tf; import tensorflow; import tf_keras; import keras; "
        "from onnx2tf.utils import common_functions; "
        "expected={'onnx2tf':'2.6.8','tensorflow':'2.21.0',"
        "'tf-keras':'2.21.0','keras':'3.15.0'}; "
        "assert all(version(name) == wanted for name, wanted in expected.items()), "
        "{name: version(name) for name in expected}"
    )
    run([str(python), "-c", probe])
    run([str(python.parent / "onnx2tf"), "--help"])


def _install_openwakeword_editable(python: Path, source: Path) -> None:
    _pip(
        python,
        "install",
        "--no-index",
        "--no-deps",
        "--no-build-isolation",
        "-e",
        str(source),
    )
    _pip(python, "check")


def _probe_piper_import(python: Path, generator: Path) -> None:
    probe = (
        "import importlib.util,pathlib,sys; "
        "p=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(p.parent)); "
        "s=importlib.util.spec_from_file_location('gi_v3_piper_probe',p); "
        "assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"
    )
    run([str(python), "-c", probe, str(generator)])


def _checkpoint_path(checkpoint_dir: Path, name: str) -> Path:
    return checkpoint_dir / f"gi-v3-{name}.tar"


def build_plan(workspace: Path, checkpoint_dir: Path, config: Path) -> dict[str, object]:
    workspace, checkpoint_dir, config = map(Path, (workspace, checkpoint_dir, config))
    train_python = _python(workspace / ".venv-train")
    train_script = workspace / "openwakeword/openwakeword/train.py"
    staged_config = workspace / "gi-v3-training.yaml"
    base = [str(train_python), str(train_script), "--training_config", str(staged_config)]
    driver = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--workspace",
        str(workspace),
        "--checkpoint-dir",
        str(checkpoint_dir),
        "--config",
        str(config),
    ]

    def command(stage: str) -> list[str]:
        return driver + ["--stage", stage]

    conversion = [
        str(workspace / ".venv-convert/bin/onnx2tf"),
        "-i",
        str(workspace / "gi-v3-work/gi.onnx"),
        "-o",
        str(workspace / "gi-v3-conversion"),
        "-kat",
        "x",
        "-ewo",
        "-efot",
        "-ens",
        "32",
    ]
    return {
        "python": "3.12.13",
        "cuda_required": True,
        "paid_runtime": False,
        "workspace": str(workspace),
        "checkpoint_dir": str(checkpoint_dir),
        "config": {"source": str(config), "staged": str(staged_config), "sha256": CONFIG_SHA256},
        "venvs": {
            "training": str(workspace / ".venv-train"),
            "conversion": str(workspace / ".venv-convert"),
        },
        "sources": REVISIONS,
        "dependency_locks": LOCK_PROVENANCE,
        "downloads": {name: item._asdict() for name, item in DOWNLOADS.items()},
        "stages": [
            {"name": "prepare", "command": command("prepare")},
            {
                "name": "generate",
                "command": command("generate"),
                "operation": base + ["--generate_clips"],
                "checkpoint": str(_checkpoint_path(checkpoint_dir, "generated-clips")),
            },
            {
                "name": "augment",
                "command": command("augment"),
                "operation": base + ["--augment_clips", "--overwrite"],
                "checkpoint": str(_checkpoint_path(checkpoint_dir, "features")),
            },
            {
                "name": "train",
                "command": command("train"),
                "operation": base + ["--train_model"],
                "checkpoint": str(_checkpoint_path(checkpoint_dir, "onnx")),
                "resume": "A lost session restarts training from the saved feature archive.",
            },
            {"name": "convert", "command": command("convert"), "operation": conversion},
            {
                "name": "verify",
                "command": command("verify"),
                "limits": {
                    "input_shape": [1, 16, 96],
                    "seeded_samples": 32,
                    "max_absolute_error": 1e-5,
                    "minimum_cosine_similarity": 0.99999,
                },
            },
            {
                "name": "bundle",
                "command": command("bundle"),
                "manifest": str(checkpoint_dir / "gi-v3-manifest.json"),
                "training_lock": str(TRAINING_LOCK),
                "conversion_lock": str(CONVERSION_LOCK),
                "training_audit": str(checkpoint_dir / "gi-v3-training-freeze.txt"),
                "conversion_audit": str(checkpoint_dir / "gi-v3-conversion-freeze.txt"),
                "checkpoint": str(_checkpoint_path(checkpoint_dir, "final-bundle")),
            },
        ],
    }


def _copy_config(source: Path, destination: Path) -> None:
    if sha256(source) != CONFIG_SHA256:
        raise RuntimeError(f"Unexpected GI v3 config SHA-256: {sha256(source)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha256(destination) != CONFIG_SHA256:
        raise RuntimeError(f"Refusing to replace a different staged config: {destination}")
    if not destination.exists():
        shutil.copyfile(source, destination)


def _write_freeze(python: Path, destination: Path) -> None:
    result = subprocess.run(
        [str(python), "-m", "pip", "freeze", "--all"], check=True, text=True, capture_output=True
    )
    atomic_text(destination, result.stdout)


def prepare(workspace: Path, checkpoint_dir: Path, config: Path) -> None:
    require_free_disk(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir = workspace / "downloads"
    _copy_config(config, workspace / "gi-v3-training.yaml")

    train_venv = workspace / ".venv-train"
    _create_venv(train_venv)
    train_python = _python(train_venv)
    _install_training_dependencies(train_python, downloads_dir)

    openwakeword = workspace / "openwakeword"
    piper = workspace / "piper-sample-generator"
    clone_pinned(
        "https://github.com/dscripka/openWakeWord.git", REVISIONS["openwakeword"], openwakeword
    )
    clone_pinned("https://github.com/rhasspy/piper-sample-generator.git", REVISIONS["piper"], piper)
    patch_train(openwakeword / "openwakeword/train.py")
    patch_openwakeword_setup(openwakeword / "setup.py")
    patch_piper(piper / "generate_samples.py")
    verify_patched_checkout(
        openwakeword,
        {
            Path("openwakeword/train.py"): TRAIN_PATCHED_SHA256,
            Path("setup.py"): OWW_SETUP_PATCHED_SHA256,
        },
        REVISIONS["openwakeword"],
    )
    verify_patched_checkout(
        piper,
        {Path("generate_samples.py"): PIPER_PATCHED_SHA256},
        REVISIONS["piper"],
    )
    _install_openwakeword_editable(train_python, openwakeword)

    audio_io = subprocess.run(
        [
            str(train_python),
            "-c",
            "import pathlib, torch_audiomentations; "
            "print(pathlib.Path(torch_audiomentations.__file__).parent / 'utils/io.py')",
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    patch_audio_io(Path(audio_io))
    run([str(train_python), "-m", "py_compile", audio_io])
    _probe_piper_import(train_python, piper / "generate_samples.py")
    require_training_cuda(train_python)

    checkpoint = piper / "models" / DOWNLOADS["piper_checkpoint"].filename
    download(DOWNLOADS["piper_checkpoint"], checkpoint)
    resources = openwakeword / "openwakeword/resources/models"
    for name in (
        "embedding_onnx",
        "embedding_tflite",
        "melspectrogram_onnx",
        "melspectrogram_tflite",
    ):
        asset = DOWNLOADS[name]
        download(asset, resources / asset.filename)
    verify_patched_checkout(openwakeword, _openwakeword_allowed_files(), REVISIONS["openwakeword"])
    audioset = downloads_dir / DOWNLOADS["audioset"].filename
    download(DOWNLOADS["audioset"], audioset)

    rir_source = workspace / "mit-rirs-source"
    clone_pinned(
        "https://huggingface.co/datasets/davidscripka/MIT_environmental_impulse_responses",
        REVISIONS["rir"],
        rir_source,
        lfs=True,
    )
    run(["git", "lfs", "pull", "--include=16khz/*.wav", "--exclude="], cwd=rir_source)
    verify_rir_checkout(rir_source)
    rir_link = workspace / "mit_rirs"
    if rir_link.exists() or rir_link.is_symlink():
        if not rir_link.is_symlink() or rir_link.resolve() != (rir_source / "16khz").resolve():
            raise RuntimeError(f"Unexpected RIR path: {rir_link}")
    else:
        rir_link.symlink_to(rir_source / "16khz", target_is_directory=True)

    audioset_output = workspace / "audioset_16k"
    manifest = audioset_output / "audioset-manifest.json"
    if not manifest.exists():
        run([str(train_python), "-c", AUDIOSET_EXTRACTOR, str(audioset), str(audioset_output)])
    verify_audioset_extract(audioset_output)

    _write_freeze(train_python, checkpoint_dir / "gi-v3-training-freeze.txt")


def prepare_conversion(workspace: Path, checkpoint_dir: Path) -> None:
    conversion_venv = workspace / ".venv-convert"
    _create_venv(conversion_venv)
    conversion_python = _python(conversion_venv)
    _install_conversion_dependencies(conversion_python, workspace / "downloads")
    _pip(conversion_python, "check")
    _probe_conversion_stack(conversion_python)
    _write_freeze(conversion_python, checkpoint_dir / "gi-v3-conversion-freeze.txt")


def _checkpoint_manifest(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _checkpoint_provenance(stage: str) -> dict[str, object]:
    return {
        "stage": stage,
        "driver_sha256": sha256(DRIVER),
        "config_sha256": CONFIG_SHA256,
        "revisions": REVISIONS,
        "dependency_locks": LOCK_PROVENANCE,
        "patched_sources": {
            "train.py": TRAIN_PATCHED_SHA256,
            "setup.py": OWW_SETUP_PATCHED_SHA256,
            "generate_samples.py": PIPER_PATCHED_SHA256,
            "torch_audiomentations/utils/io.py": AUDIO_IO_PATCHED_SHA256,
        },
    }


def _checkpoint_valid(path: Path, stage: str | None = None) -> bool:
    record_path = _checkpoint_manifest(path)
    if not path.is_file() or not record_path.is_file():
        return False
    try:
        record = json.loads(record_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    provenance = _checkpoint_provenance(record.get("stage"))
    if stage is not None and record.get("stage") != stage:
        return False
    return (
        record.get("bytes") == path.stat().st_size
        and record.get("sha256") == sha256(path)
        and all(record.get(key) == value for key, value in provenance.items())
    )


def _restore_checkpoint(path: Path, workspace: Path, stage: str | None = None) -> None:
    if not _checkpoint_valid(path, stage):
        raise RuntimeError(f"Invalid checkpoint archive: {path}")
    with tarfile.open(path) as archive:
        archive.extractall(workspace, filter="data")


def _archive_checkpoint(
    path: Path, workspace: Path, relative_paths: Sequence[Path], stage: str
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = Path(f"{path}.part")
    with tarfile.open(part, "w") as archive:
        for relative in relative_paths:
            source = workspace / relative
            if not source.exists():
                raise RuntimeError(f"Missing checkpoint output: {source}")
            archive.add(source, arcname=str(relative), recursive=True)
    os.replace(part, path)
    record = {
        **_checkpoint_provenance(stage),
        "members": [str(relative) for relative in relative_paths],
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    atomic_text(
        _checkpoint_manifest(path),
        json.dumps(record, indent=2, sort_keys=True) + "\n",
    )


STAGE_OUTPUTS = {
    "generate": (
        Path("gi-v3-work/gi/positive_train"),
        Path("gi-v3-work/gi/positive_test"),
        Path("gi-v3-work/gi/negative_train"),
        Path("gi-v3-work/gi/negative_test"),
    ),
    "augment": (
        Path("gi-v3-work/gi/positive_features_train.npy"),
        Path("gi-v3-work/gi/positive_features_test.npy"),
        Path("gi-v3-work/gi/negative_features_train.npy"),
        Path("gi-v3-work/gi/negative_features_test.npy"),
    ),
    "train": (Path("gi-v3-work/gi.onnx"),),
}

GENERATED_COUNTS = {
    Path("gi-v3-work/gi/positive_train"): 20_000,
    Path("gi-v3-work/gi/positive_test"): 2_000,
    Path("gi-v3-work/gi/negative_train"): 20_000,
    Path("gi-v3-work/gi/negative_test"): 2_000,
}

FEATURE_SHAPES = {
    Path("gi-v3-work/gi/positive_features_train.npy"): (20_000, 16, 96),
    Path("gi-v3-work/gi/positive_features_test.npy"): (2_000, 16, 96),
    Path("gi-v3-work/gi/negative_features_train.npy"): (20_000, 16, 96),
    Path("gi-v3-work/gi/negative_features_test.npy"): (2_000, 16, 96),
}


def _stage_archive_outputs(workspace: Path, stage: str) -> tuple[Path, ...]:
    outputs = STAGE_OUTPUTS[stage]
    external = Path("gi-v3-work/gi.onnx.data")
    if stage == "train" and (workspace / external).is_file():
        return outputs + (external,)
    return outputs


def _clear_stage_outputs(workspace: Path, stage: str) -> None:
    outputs = set(STAGE_OUTPUTS[stage])
    if stage == "train":
        outputs.add(Path("gi-v3-work/gi.onnx.data"))
    for relative in outputs:
        path = workspace / relative
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()


def _npy_metadata(workspace: Path, paths: Sequence[Path]) -> dict[str, dict[str, object]]:
    result = subprocess.run(
        [
            str(_python(workspace / ".venv-train")),
            "-c",
            "import json,numpy as np,sys; print(json.dumps({p: {'shape': list((a := np.load(p, mmap_mode='r')).shape), 'dtype': str(a.dtype)} for p in sys.argv[1:]}))",
            *(str(path) for path in paths),
        ],
        cwd=workspace,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def _onnx_metadata(workspace: Path, path: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            str(_python(workspace / ".venv-train")),
            "-c",
            "import json,onnxruntime as ort,sys; i=ort.InferenceSession(sys.argv[1], providers=['CPUExecutionProvider']).get_inputs()[0]; print(json.dumps({'name': i.name, 'shape': i.shape}))",
            str(path),
        ],
        cwd=workspace,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def validate_stage_outputs(workspace: Path, stage: str) -> None:
    if stage == "generate":
        for relative, expected in GENERATED_COUNTS.items():
            actual = len(list((workspace / relative).glob("*.wav")))
            if actual != expected:
                raise RuntimeError(
                    f"Wrong generated WAV count for {relative}: {actual}, expected {expected}"
                )
    elif stage == "augment":
        metadata = _npy_metadata(workspace, tuple(FEATURE_SHAPES))
        for relative, expected in FEATURE_SHAPES.items():
            actual = metadata.get(str(relative), {})
            if actual.get("shape") != list(expected) or actual.get("dtype") != "float32":
                raise RuntimeError(
                    f"Wrong feature array for {relative}: {actual}, expected {expected} float32"
                )
    elif stage == "train":
        relative = STAGE_OUTPUTS["train"][0]
        actual = _onnx_metadata(workspace, relative)
        if actual != {"name": "x", "shape": [1, 16, 96]}:
            raise RuntimeError(f"Wrong trained ONNX input: {actual}")
    else:
        raise ValueError(f"Unknown training stage: {stage}")


def _verify_stage_inputs(workspace: Path, stage: str) -> None:
    _copy_config(workspace / "gi-v3-training.yaml", workspace / "gi-v3-training.yaml")
    verify_patched_checkout(
        workspace / "openwakeword",
        _openwakeword_allowed_files(),
        REVISIONS["openwakeword"],
    )
    verify_patched_checkout(
        workspace / "piper-sample-generator",
        {Path("generate_samples.py"): PIPER_PATCHED_SHA256},
        REVISIONS["piper"],
    )
    audio_io = (
        workspace / ".venv-train/lib/python3.12/site-packages/torch_audiomentations/utils/io.py"
    )
    if not audio_io.is_file() or sha256(audio_io) != AUDIO_IO_PATCHED_SHA256:
        raise RuntimeError(f"Unexpected patched torch-audiomentations source: {audio_io}")
    if stage == "generate":
        verify_file(
            workspace / "piper-sample-generator/models" / DOWNLOADS["piper_checkpoint"].filename,
            DOWNLOADS["piper_checkpoint"],
        )
    if stage == "augment":
        verify_rir_checkout(workspace / "mit-rirs-source")
        verify_audioset_extract(workspace / "audioset_16k")
        resources = workspace / "openwakeword/openwakeword/resources/models"
        for name in (
            "embedding_onnx",
            "embedding_tflite",
            "melspectrogram_onnx",
            "melspectrogram_tflite",
        ):
            verify_file(resources / DOWNLOADS[name].filename, DOWNLOADS[name])
    if stage == "train":
        require_free_disk(workspace)
        for name in ("acav_features", "validation_features"):
            asset = DOWNLOADS[name]
            path = workspace / asset.filename
            download(asset, path)
            verify_file(path, asset)


def run_training_stage(workspace: Path, checkpoint_dir: Path, stage: str) -> None:
    archive_name = {"generate": "generated-clips", "augment": "features", "train": "onnx"}[stage]
    checkpoint = _checkpoint_path(checkpoint_dir, archive_name)
    if checkpoint.exists() or _checkpoint_manifest(checkpoint).exists():
        if not _checkpoint_valid(checkpoint, stage):
            raise RuntimeError(f"Checkpoint archive or sidecar failed verification: {checkpoint}")
        _clear_stage_outputs(workspace, stage)
        _restore_checkpoint(checkpoint, workspace, stage)
        validate_stage_outputs(workspace, stage)
        return
    _verify_stage_inputs(workspace, stage)
    flags = {
        "generate": ["--generate_clips"],
        "augment": ["--augment_clips", "--overwrite"],
        "train": ["--train_model"],
    }
    run(
        [
            str(_python(workspace / ".venv-train")),
            str(workspace / "openwakeword/openwakeword/train.py"),
            "--training_config",
            str(workspace / "gi-v3-training.yaml"),
            *flags[stage],
        ],
        cwd=workspace,
    )
    validate_stage_outputs(workspace, stage)
    _archive_checkpoint(checkpoint, workspace, _stage_archive_outputs(workspace, stage), stage)


def convert(workspace: Path, checkpoint_dir: Path) -> None:
    onnx = workspace / "gi-v3-work/gi.onnx"
    if not onnx.is_file():
        raise RuntimeError(f"Missing trained ONNX model: {onnx}")
    validate_stage_outputs(workspace, "train")
    prepare_conversion(workspace, checkpoint_dir)
    conversion = workspace / "gi-v3-conversion"
    if conversion.exists():
        shutil.rmtree(conversion)
    environment = os.environ.copy()
    conversion_bin = workspace / ".venv-convert/bin"
    previous_path = environment.get("PATH")
    environment["PATH"] = (
        f"{conversion_bin}{os.pathsep}{previous_path}" if previous_path else str(conversion_bin)
    )
    run(
        [
            str(workspace / ".venv-convert/bin/onnx2tf"),
            "-i",
            str(onnx),
            "-o",
            str(conversion),
            "-kat",
            "x",
            "-ewo",
            "-efot",
            "-ens",
            "32",
        ],
        cwd=workspace,
        env=environment,
    )
    generated = conversion / "gi_float32.tflite"
    if not generated.is_file():
        raise RuntimeError(f"onnx2tf did not create {generated}")
    for name in CONVERSION_REPORTS:
        if not (conversion / name).is_file():
            raise RuntimeError(f"onnx2tf did not create promotion report: {conversion / name}")
    shutil.copyfile(generated, workspace / "gi-v3-work/gi-v3.tflite")


def verify_candidate(workspace: Path) -> None:
    run(
        [
            str(_python(workspace / ".venv-convert")),
            "-c",
            PARITY_VERIFIER,
            str(workspace / "gi-v3-work/gi.onnx"),
            str(workspace / "gi-v3-work/gi-v3.tflite"),
            str(workspace / "gi-v3-work/gi-v3-parity.json"),
        ]
    )


def _bundle_artifacts(workspace: Path, checkpoint_dir: Path) -> dict[str, Path]:
    artifacts = {
        "gi-v3-training.yaml": workspace / "gi-v3-training.yaml",
        "models/gi.onnx": workspace / "gi-v3-work/gi.onnx",
        "models/gi-v3.tflite": workspace / "gi-v3-work/gi-v3.tflite",
        "reports/gi-v3-parity.json": workspace / "gi-v3-work/gi-v3-parity.json",
        "conversion/gi_float32.tflite": workspace / "gi-v3-conversion/gi_float32.tflite",
        "conversion/gi_accuracy_report.json": (
            workspace / "gi-v3-conversion/gi_accuracy_report.json"
        ),
        "conversion/gi_accuracy_comparison_report.json": (
            workspace / "gi-v3-conversion/gi_accuracy_comparison_report.json"
        ),
        "audit/gi-v3-training-freeze.txt": checkpoint_dir / "gi-v3-training-freeze.txt",
        "audit/gi-v3-conversion-freeze.txt": checkpoint_dir / "gi-v3-conversion-freeze.txt",
        "locks/gi-v3-training.lock": TRAINING_LOCK,
        "locks/gi-v3-conversion.lock": CONVERSION_LOCK,
        "workflow/train_gi_v3_colab.py": DRIVER,
        "patched-sources/openwakeword-train.py": (workspace / "openwakeword/openwakeword/train.py"),
        "patched-sources/openwakeword-setup.py": workspace / "openwakeword/setup.py",
        "patched-sources/piper-generate_samples.py": (
            workspace / "piper-sample-generator/generate_samples.py"
        ),
        "patched-sources/torch-audiomentations-io.py": (
            workspace / ".venv-train/lib/python3.12/site-packages/torch_audiomentations/utils/io.py"
        ),
    }
    external_data = workspace / "gi-v3-work/gi.onnx.data"
    if external_data.is_file():
        artifacts["models/gi.onnx.data"] = external_data
    return artifacts


def _environment_provenance() -> dict[str, object]:
    return {
        "kind": "checked-in hash locks plus verified direct artifacts",
        "exact_first_install_replay": True,
        "python": "3.12.13",
        "dependency_locks": LOCK_PROVENANCE,
        "audit_snapshots": (
            "gi-v3-training-freeze.txt",
            "gi-v3-conversion-freeze.txt",
        ),
    }


def _stage_checkpoint_records(checkpoint_dir: Path) -> dict[str, dict[str, object]]:
    records = {}
    for stage, name in (
        ("generate", "generated-clips"),
        ("augment", "features"),
        ("train", "onnx"),
    ):
        checkpoint = _checkpoint_path(checkpoint_dir, name)
        if not _checkpoint_valid(checkpoint, stage):
            raise RuntimeError(f"Missing or invalid {stage} stage checkpoint: {checkpoint}")
        record = json.loads(_checkpoint_manifest(checkpoint).read_text())
        records[stage] = {"archive": checkpoint.name, **record}
    return records


def bundle(workspace: Path, checkpoint_dir: Path) -> None:
    training_lock = checkpoint_dir / "gi-v3-training-freeze.txt"
    conversion_lock = checkpoint_dir / "gi-v3-conversion-freeze.txt"
    _write_freeze(_python(workspace / ".venv-train"), training_lock)
    _write_freeze(_python(workspace / ".venv-convert"), conversion_lock)
    artifacts = _bundle_artifacts(workspace, checkpoint_dir)
    for path in artifacts.values():
        if not path.is_file():
            raise RuntimeError(f"Missing final artifact: {path}")
    expected_hashes = {
        "gi-v3-training.yaml": CONFIG_SHA256,
        "patched-sources/openwakeword-train.py": TRAIN_PATCHED_SHA256,
        "patched-sources/openwakeword-setup.py": OWW_SETUP_PATCHED_SHA256,
        "patched-sources/piper-generate_samples.py": PIPER_PATCHED_SHA256,
        "patched-sources/torch-audiomentations-io.py": AUDIO_IO_PATCHED_SHA256,
        "locks/gi-v3-training.lock": TRAINING_LOCK_SHA256,
        "locks/gi-v3-conversion.lock": CONVERSION_LOCK_SHA256,
        "workflow/train_gi_v3_colab.py": sha256(DRIVER),
    }
    for name, expected in expected_hashes.items():
        actual = sha256(artifacts[name])
        if actual != expected:
            raise RuntimeError(f"Unexpected final artifact SHA-256 for {name}: {actual}")
    stage_checkpoints = _stage_checkpoint_records(checkpoint_dir)
    manifest = {
        "model": "gi-v3",
        "human_audio_used": False,
        "paid_runtime_requested": False,
        "config_sha256": CONFIG_SHA256,
        "sources": REVISIONS,
        "inputs": {name: item._asdict() for name, item in DOWNLOADS.items()},
        "patches": {
            "train.py": TRAIN_PATCHED_SHA256,
            "setup.py": OWW_SETUP_PATCHED_SHA256,
            "generate_samples.py": PIPER_PATCHED_SHA256,
            "torch_audiomentations/utils/io.py": AUDIO_IO_PATCHED_SHA256,
        },
        "environment_records": _environment_provenance(),
        "stage_checkpoints": stage_checkpoints,
        "artifacts": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in artifacts.items()
        },
    }
    manifest_path = checkpoint_dir / "gi-v3-manifest.json"
    atomic_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    archive_path = _checkpoint_path(checkpoint_dir, "final-bundle")
    part = Path(f"{archive_path}.part")
    with tarfile.open(part, "w") as archive:
        for name, path in artifacts.items():
            archive.add(path, arcname=name)
        archive.add(manifest_path, arcname=manifest_path.name)
    os.replace(part, archive_path)
    record = {
        **_checkpoint_provenance("bundle"),
        "members": [*artifacts, manifest_path.name],
        "bytes": archive_path.stat().st_size,
        "sha256": sha256(archive_path),
    }
    atomic_text(
        _checkpoint_manifest(archive_path),
        json.dumps(record, indent=2, sort_keys=True) + "\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("/content/gi-v3"))
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--stage",
        choices=("all", "prepare", "generate", "augment", "train", "convert", "verify", "bundle"),
        default="all",
    )
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(args.workspace, args.checkpoint_dir, args.config)
    if args.plan or args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    require_host_runtime()
    require_checkpoint_storage(args.checkpoint_dir)
    stages = ("prepare", "generate", "augment", "train", "convert", "verify", "bundle")
    selected = stages if args.stage == "all" else (args.stage,)
    for stage in selected:
        if stage == "prepare":
            prepare(args.workspace, args.checkpoint_dir, args.config)
        elif stage in STAGE_OUTPUTS:
            run_training_stage(args.workspace, args.checkpoint_dir, stage)
        elif stage == "convert":
            convert(args.workspace, args.checkpoint_dir)
        elif stage == "verify":
            verify_candidate(args.workspace)
        elif stage == "bundle":
            bundle(args.workspace, args.checkpoint_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
