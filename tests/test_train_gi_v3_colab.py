"""Checks for the reproducible GI v3 Colab training driver."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/train_gi_v3_colab.py"
CONFIG = (
    ROOT
    / "playbooks/argocd/applications/home-automation/voice-assistant/models"
    / "gi-v3-training.yaml"
)
NOTEBOOK = CONFIG.with_name("gi-v3-training-colab.ipynb")
PINNED_BROWSER_REVISION = "5212621514e91fde371b455603f090aad7cea629"


def load_driver():
    spec = importlib.util.spec_from_file_location("train_gi_v3_colab", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_colab_notebook_is_a_two_cell_pinned_browser_checkpoint_launcher() -> None:
    notebook = json.loads(NOTEBOOK.read_text())
    cells = notebook["cells"]

    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["accelerator"] == "GPU"
    assert len(cells) == 2
    assert [cell["cell_type"] for cell in cells] == ["code", "code"]
    assert all(cell["execution_count"] is None and cell["outputs"] == [] for cell in cells)

    setup = "".join(cells[0]["source"])
    launch = "".join(cells[1]["source"])
    compile(setup, str(NOTEBOOK), "exec")
    compile(launch, str(NOTEBOOK), "exec")
    assert 'TARGET = "generate"' in setup
    assert "generate, augment, train, or finish" in setup
    assert f'SOYSPRAY_REVISION = "{PINNED_BROWSER_REVISION}"' in launch
    assert "https://github.com/kpoxo6op/soyspray.git" in launch
    assert '"fetch", "--depth", "1", "origin", SOYSPRAY_REVISION' in launch
    assert '"checkout", "--detach", SOYSPRAY_REVISION' in launch
    assert '"scripts/gi_v3_browser_checkpoints.py"' in launch
    assert '"run", "--target", TARGET' in launch
    assert "actual != SOYSPRAY_REVISION" in launch

    rendered = json.dumps(notebook).casefold()
    assert "drive.mount" not in rendered
    assert "authenticate_user" not in rendered
    assert "telegram" not in rendered
    assert "human audio" not in rendered
    assert "paid runtime" not in rendered


def test_sources_and_large_inputs_are_immutable() -> None:
    driver = load_driver()

    assert driver.REVISIONS == {
        "openwakeword": "368c03716d1e92591906a84949bc477f3a834455",
        "piper": "213d4d561ab8a84f71de7dddac827cb07e92c031",
        "audioset": "0c609e8302cf139307f639c57652032af0a88041",
        "features": "985bf1b47e7f19c07741af82bfe32d5a9dc56096",
        "rir": "b824a1ef2821f112fda0b9cb26e4278c62b425bb",
    }

    expected = {
        "pip": (
            "https://files.pythonhosted.org/packages/b7/3f/"
            "945ef7ab14dc4f9d7f40288d2df998d1837ee0888ec3659c813487572faa/"
            "pip-25.2-py3-none-any.whl",
            1_752_557,
            "6d67a2b4e7f14d8b31b8b52648866fa717f45a1eb70e83002f4331d07e953717",
        ),
        "setuptools": (
            "https://files.pythonhosted.org/packages/94/b8/"
            "f1f62a5e3c0ad2ff1d189590bfa4c46b4f3b6e49cef6f26c6ee4e575394d/"
            "setuptools-80.10.2-py3-none-any.whl",
            1_064_234,
            "95b30ddfb717250edb492926c92b5221f7ef3fbcc2b07579bcd4a27da21d0173",
        ),
        "flit_core": (
            "https://files.pythonhosted.org/packages/f2/65/"
            "b6ba90634c984a4fcc02c7e3afe523fef500c4980fec67cc27536ee50acf/"
            "flit_core-3.12.0-py3-none-any.whl",
            45_594,
            "e7a0304069ea895172e3c7bb703292e992c5d1555dd1233ab7b5621b5b69e62c",
        ),
        "wheel": (
            "https://files.pythonhosted.org/packages/0b/2c/"
            "87f3254fd8ffd29e4c02732eee68a83a1d3c346ae39bc6822dcbcb697f2b/"
            "wheel-0.45.1-py3-none-any.whl",
            72_494,
            "708e7481cc80179af0e556bbf0cc00b8444c7321e2700b8d8580231d13017248",
        ),
        "acoustics_sdist": (
            "https://files.pythonhosted.org/packages/28/55/"
            "6039f24c69f2c3fcdb9ca1655a28fe9bd66a698479fc12e79e8dcd9efd1f/"
            "acoustics-0.2.6.tar.gz",
            3_476_036,
            "d02bcc84251cfa2edd3e21c7f885dd963f8e8c587f975c2f9d4e1d9b142bcc52",
        ),
        "pronouncing_sdist": (
            "https://files.pythonhosted.org/packages/7f/c6/"
            "9dc74a3ddca71c492e224116b6654592bfe5717b4a78582e4d9c3345d153/"
            "pronouncing-0.2.0.tar.gz",
            17_562,
            "ff7856e1d973b3e16ff490c5cf1abdb52f08f45e2c35e463249b75741331e7c4",
        ),
        "deep_phonemizer_sdist": (
            "https://files.pythonhosted.org/packages/6f/39/"
            "f04c12980b6d639247b7d544abcd5b5e2727ee2b9c5f2e01e8a0bf735041/"
            "deep-phonemizer-0.0.19.tar.gz",
            29_731,
            "6f47af558f0a51eec20080fc2dce999010d9342586ad42350496da0ba1610ec3",
        ),
        "speexdsp_ns": (
            "https://files.pythonhosted.org/packages/7b/14/"
            "d9fd843472f82853643c4ae09835c76bfb19ce7e712586cfc1318030503f/"
            "speexdsp_ns-0.1.2-cp312-cp312-manylinux_2_28_x86_64.whl",
            161_569,
            "c2c73c2f132212fecfff52a689594f925453ff521fec336411149256aedcd819",
        ),
        "piper_checkpoint": (
            "https://github.com/rhasspy/piper-sample-generator/releases/"
            "download/v2.0.0/en_US-libritts_r-medium.pt",
            204_089_915,
            "e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6",
        ),
        "embedding_onnx": (
            "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
            "embedding_model.onnx",
            1_326_578,
            "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",
        ),
        "embedding_tflite": (
            "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
            "embedding_model.tflite",
            1_330_312,
            "c0aea21eb84a4ce90a08c870da41b7a7173b45269e6a3207c71d67c40f3a59d8",
        ),
        "melspectrogram_onnx": (
            "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx",
            1_087_958,
            "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",
        ),
        "melspectrogram_tflite": (
            "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/"
            "melspectrogram.tflite",
            1_092_516,
            "96fa0adccb6e8cf95cb14465409a1a2898ee4a96a85bb9ed3c7eb0e68bf163e8",
        ),
        "audioset": (
            "https://huggingface.co/datasets/agkphysics/AudioSet/resolve/"
            "0c609e8302cf139307f639c57652032af0a88041/data/bal_train/"
            "00.parquet?download=true",
            687_636_067,
            "b433e7bcf3bbdfb0488791fceae1eb7100711d13093d22e2253f15d2dcabc084",
        ),
        "acav_features": (
            "https://huggingface.co/datasets/davidscripka/openwakeword_features/"
            "resolve/985bf1b47e7f19c07741af82bfe32d5a9dc56096/"
            "openwakeword_features_ACAV100M_2000_hrs_16bit.npy?download=true",
            17_280_000_128,
            "721a66d0682c65a1b5c1da0aa109409cede1d20e28b15235c344b000cbb7654f",
        ),
        "validation_features": (
            "https://huggingface.co/datasets/davidscripka/openwakeword_features/"
            "resolve/985bf1b47e7f19c07741af82bfe32d5a9dc56096/"
            "validation_set_features.npy?download=true",
            184_836_608,
            "a56a8a0f8e0efb91900acc6de4c0cdf4c564842e8475a7d49b36c039e17a690f",
        ),
        "piper_phonemize": (
            "https://files.pythonhosted.org/packages/76/3f/"
            "f3d1e2d5ef7005abf6f7812d06b471788346dda2b82de285ae87ab45a9fa/"
            "piper_phonemize_cross-1.2.1-cp312-cp312-manylinux_2_28_x86_64.whl",
            15_575_585,
            "f171d5bd5a7e19871c9ef6b5a21390020587034ad140bc678d9360bc1627df1d",
        ),
        "onnxruntime_gpu": (
            "https://files.pythonhosted.org/packages/ed/cd/"
            "98ea1ef90c5e51de69239881522a4c115a009dba99d83fd8e2606b33358d/"
            "onnxruntime_gpu-1.20.0-cp312-cp312-manylinux_2_27_x86_64."
            "manylinux_2_28_x86_64.whl",
            291_507_294,
            "06398420c363b7e400de98deb8bc238fcff98adafe8eeda6ff96a94e20713ac0",
        ),
    }
    for name, (url, size, sha256) in expected.items():
        asset = driver.DOWNLOADS[name]
        assert (asset.url, asset.size, asset.sha256) == (url, size, sha256)
    assert "piper-phonemize==1.1.0" not in driver.TRAIN_REQUIREMENTS
    assert "onnxruntime-gpu==1.20.1" not in driver.TRAIN_REQUIREMENTS
    assert "webrtcvad==2.0.10" not in driver.TRAIN_REQUIREMENTS
    assert "webrtcvad-wheels==2.0.14" in driver.TRAIN_REQUIREMENTS


def test_cuda_wheels_are_cp312_cu121_and_hash_pinned() -> None:
    driver = load_driver()
    expected = {
        "torch": (
            780_367_618,
            "c4e0eb78c24d6991db93d86f06809edb10ac15220363b04ef18e22da50f059fe",
        ),
        "torchvision": (
            7_283_863,
            "e794f7728dd5cec0d9bfa12749019d072a841e8dc2cdc1aba09afc63c5bb7ec3",
        ),
        "torchaudio": (
            3_413_081,
            "6f06233a9e32b1997ebd1b9736321cd88e6f156aeef225529ac31dc5bb056024",
        ),
    }
    for name, (size, sha256) in expected.items():
        asset = driver.DOWNLOADS[name]
        assert "cu121" in asset.url
        assert "cp312-cp312-linux_x86_64.whl" in asset.url
        assert (asset.size, asset.sha256) == (size, sha256)


def test_training_compatibility_requirements_match_the_validated_lock() -> None:
    driver = load_driver()

    assert {
        "setuptools==80.10.2",
        "flit-core==3.12.0",
        "wheel==0.45.1",
        "numpy==2.0.2",
        "datasets==4.0.0",
        "pyarrow==18.1.0",
        "numba==0.60.0",
        "llvmlite==0.43.0",
        "protobuf==7.35.1",
        "scikit-learn==1.6.1",
        "speexdsp-ns==0.1.2",
        "backports-strenum==1.2.8",
    }.issubset(driver.TRAIN_REQUIREMENTS)
    assert driver.CONVERSION_REQUIREMENTS == (
        "onnx2tf==2.6.8",
        "ai-edge-litert==2.1.2",
        "backports-strenum==1.2.8",
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


def test_checked_in_hash_locks_are_immutable_and_complete() -> None:
    driver = load_driver()
    locks = {
        driver.TRAINING_LOCK: driver.TRAINING_LOCK_SHA256,
        driver.CONVERSION_LOCK: driver.CONVERSION_LOCK_SHA256,
    }

    for path, expected in locks.items():
        assert path.is_file()
        assert driver.sha256(path) == expected
        text = path.read_text()
        assert "--hash=sha256:" in text
        assert " @ " not in text
    training = driver.TRAINING_LOCK.read_text()
    assert "webrtcvad-wheels==2.0.14" in training
    assert "backports-strenum==1.2.8" in training
    assert "backports-strenum==1.3.1" not in training
    conversion = driver.CONVERSION_LOCK.read_text()
    assert "backports-strenum==1.2.8" in conversion
    assert "backports-strenum==1.3.1" not in conversion
    assert "tensorflow==2.21.0" in conversion
    assert "tf-keras==2.21.0" in conversion
    assert "keras==3.15.0" in conversion
    for direct in (
        "torch",
        "torchvision",
        "torchaudio",
        "onnxruntime-gpu",
        "piper-phonemize-cross",
        "acoustics",
        "pronouncing",
        "deep-phonemizer",
        "speexdsp-ns",
    ):
        assert not any(line.startswith(f"{direct}==") for line in training.splitlines())


def test_lock_install_rejects_drift_and_requires_hashes_and_wheels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    lock = tmp_path / "requirements.lock"
    lock.write_text("example==1.0 --hash=sha256:" + "0" * 64 + "\n")
    expected = digest(lock.read_bytes())
    commands = []
    monkeypatch.setattr(
        driver,
        "_pip",
        lambda python, *arguments: commands.append((python, list(arguments))),
    )

    driver._install_lock(Path("/venv/python"), lock, expected)

    assert commands == [
        (
            Path("/venv/python"),
            ["install", "--require-hashes", "--only-binary=:all:", "-r", str(lock)],
        )
    ]
    lock.write_text(lock.read_text() + "# drift\n")
    with pytest.raises(RuntimeError, match="lock SHA-256"):
        driver._install_lock(Path("/venv/python"), lock, expected)


def test_clean_venv_bootstraps_only_from_the_verified_pip_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    commands = []
    monkeypatch.setattr(
        driver,
        "run",
        lambda command, **kwargs: commands.append((list(command), kwargs)),
    )
    venv = tmp_path / ".venv-train"

    driver._create_venv(venv)
    driver._bootstrap_pip(venv / "bin/python", tmp_path / "pip.whl")

    assert commands[0][0] == [
        driver.sys.executable,
        "-m",
        "venv",
        "--without-pip",
        str(venv),
    ]
    bootstrap, options = commands[1]
    assert bootstrap == [
        str(venv / "bin/python"),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        str(tmp_path / "pip.whl"),
    ]
    assert options["env"]["PYTHONPATH"] == str(tmp_path / "pip.whl")


def test_training_install_splits_binary_lock_and_verified_sdists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    events = []
    monkeypatch.setattr(
        driver,
        "_verify_lock",
        lambda path, expected: events.append(("verify-lock", path, expected)),
    )
    monkeypatch.setattr(
        driver,
        "download",
        lambda asset, path: events.append(("download", path.name)),
    )
    monkeypatch.setattr(
        driver,
        "_bootstrap_pip",
        lambda python, wheel: events.append(("bootstrap", python, wheel.name)),
    )
    monkeypatch.setattr(
        driver,
        "_pip",
        lambda python, *arguments: events.append(("pip", python, list(arguments))),
    )
    monkeypatch.setattr(
        driver,
        "_install_lock",
        lambda python, path, expected: events.append(("install-lock", python, path, expected)),
    )
    python = tmp_path / ".venv-train/bin/python"

    driver._install_training_dependencies(python, tmp_path / "downloads")

    assert events[0] == (
        "verify-lock",
        driver.TRAINING_LOCK,
        driver.TRAINING_LOCK_SHA256,
    )
    assert events[1][0:2] == ("download", driver.DOWNLOADS["pip"].filename)
    assert next(event for event in events if event[0] == "bootstrap") == (
        "bootstrap",
        python,
        driver.DOWNLOADS["pip"].filename,
    )
    pip_calls = [event[2] for event in events if event[0] == "pip"]
    assert [
        "install",
        "--no-index",
        "--no-deps",
        *[
            str(tmp_path / "downloads" / driver.DOWNLOADS[name].filename)
            for name in ("setuptools", "flit_core", "wheel")
        ],
    ] in pip_calls
    assert [
        "install",
        "--no-index",
        "--no-deps",
        *[
            str(tmp_path / "downloads" / driver.DOWNLOADS[name].filename)
            for name in (
                "torch",
                "torchvision",
                "torchaudio",
                "piper_phonemize",
                "onnxruntime_gpu",
                "speexdsp_ns",
            )
        ],
    ] in pip_calls
    lock_index = next(index for index, event in enumerate(events) if event[0] == "install-lock")
    for name in ("acoustics_sdist", "pronouncing_sdist", "deep_phonemizer_sdist"):
        call = [
            "install",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            str(tmp_path / "downloads" / driver.DOWNLOADS[name].filename),
        ]
        assert call in pip_calls
        assert (
            next(
                index
                for index, event in enumerate(events)
                if event[0] == "pip" and event[2] == call
            )
            > lock_index
        )


def test_openwakeword_editable_install_is_metadata_checked_after_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = load_driver()
    calls = []
    monkeypatch.setattr(
        driver,
        "_pip",
        lambda python, *arguments: calls.append((python, list(arguments))),
    )
    python = Path("/venv/bin/python")
    source = Path("/work/openwakeword")

    driver._install_openwakeword_editable(python, source)

    assert calls == [
        (
            python,
            [
                "install",
                "--no-index",
                "--no-deps",
                "--no-build-isolation",
                "-e",
                str(source),
            ],
        ),
        (python, ["check"]),
    ]


def test_conversion_install_uses_verified_bootstrap_and_hash_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    events = []
    monkeypatch.setattr(
        driver,
        "_verify_lock",
        lambda path, expected: events.append(("verify-lock", path, expected)),
    )
    monkeypatch.setattr(
        driver,
        "download",
        lambda asset, path: events.append(("download", path.name)),
    )
    monkeypatch.setattr(
        driver,
        "_bootstrap_pip",
        lambda python, wheel: events.append(("bootstrap", python, wheel.name)),
    )
    monkeypatch.setattr(
        driver,
        "_install_lock",
        lambda python, path, expected: events.append(("install-lock", python, path, expected)),
    )
    python = tmp_path / ".venv-convert/bin/python"

    driver._install_conversion_dependencies(python, tmp_path / "downloads")

    assert events == [
        ("verify-lock", driver.CONVERSION_LOCK, driver.CONVERSION_LOCK_SHA256),
        ("download", driver.DOWNLOADS["pip"].filename),
        ("bootstrap", python, driver.DOWNLOADS["pip"].filename),
        ("install-lock", python, driver.CONVERSION_LOCK, driver.CONVERSION_LOCK_SHA256),
    ]


def test_conversion_stack_probe_imports_onnx2tf_tensorflow_and_tf_keras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = load_driver()
    commands = []
    monkeypatch.setattr(driver, "run", lambda command, **kwargs: commands.append(list(command)))
    python = Path("/venv/bin/python")

    driver._probe_conversion_stack(python)

    assert commands[0][:2] == [str(python), "-c"]
    source = commands[0][2]
    assert "import onnx2tf" in source
    assert "import tensorflow" in source
    assert "import tf_keras" in source
    assert "onnx2tf.utils import common_functions" in source
    for package, version in (
        ("onnx2tf", "2.6.8"),
        ("tensorflow", "2.21.0"),
        ("tf-keras", "2.21.0"),
        ("keras", "3.15.0"),
    ):
        assert repr(package) in source
        assert repr(version) in source
    assert commands[1] == [str(python.parent / "onnx2tf"), "--help"]


def test_download_command_resumes_into_part_file() -> None:
    driver = load_driver()
    destination = Path("/content/gi-v3/downloads/a.bin")

    command, part = driver.download_command(driver.DOWNLOADS["audioset"], destination)

    assert part == Path(f"{destination}.part")
    assert command[:4] == ["curl", "--fail", "--location", "--continue-at"]
    assert command[4] == "-"
    assert command[-2:] == ["--output", str(part)]


def test_completed_partial_download_is_verified_and_promoted_without_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    data = b"complete"
    asset = driver.Download("https://invalid.example/file", "file", len(data), digest(data))
    destination = tmp_path / "file"
    Path(f"{destination}.part").write_bytes(data)
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("curl must not run for a complete verified part"),
    )

    driver.download(asset, destination)

    assert destination.read_bytes() == data
    assert not Path(f"{destination}.part").exists()


def test_train_patch_is_exact_and_fixes_both_upstream_bugs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    source = (
        "before\r\n"
        + 'default="False",\r\n' * 5
        + '            adversarial_texts = config["custom_negative_phrases"]\r\n' * 2
        + '        if n_current_samples <= 0.95*config["n_samples"]:\r\n' * 2
        + '        if n_current_samples <= 0.95*config["n_samples_val"]:\r\n' * 2
        + '                          os.path.join(output_dir, model_name + ".onnx"), opset_version=13)\r\n'
        + "                             output_dir=positive_test_output_dir, auto_reduce_batch_size=True)\r\n"
        + "                             output_dir=negative_test_output_dir, auto_reduce_batch_size=True)\r\n"
        + '                    self.best_val_accuracy = self.history["val_accuracy"][-1]\r\n'
        + "after\r\n"
    ).encode()
    normalized = source.decode().replace("\r\n", "\n")
    patched = (
        normalized.replace('default="False",', "default=False,")
        .replace(
            '            adversarial_texts = config["custom_negative_phrases"]',
            '            adversarial_texts = list(config["custom_negative_phrases"])',
        )
        .replace(
            '        if n_current_samples <= 0.95*config["n_samples"]:',
            '        if n_current_samples < config["n_samples"]:',
        )
        .replace(
            '        if n_current_samples <= 0.95*config["n_samples_val"]:',
            '        if n_current_samples < config["n_samples_val"]:',
        )
        .replace(
            '                          os.path.join(output_dir, model_name + ".onnx"), opset_version=13)',
            '                          os.path.join(output_dir, model_name + ".onnx"), opset_version=13, input_names=["x"])',
        )
        .replace(
            "                             output_dir=positive_test_output_dir, auto_reduce_batch_size=True)",
            "                             output_dir=positive_test_output_dir, auto_reduce_batch_size=True,\n"
            '                             file_names=[uuid.uuid4().hex + ".wav" for i in range(config["n_samples_val"])])',
        )
        .replace(
            "                             output_dir=negative_test_output_dir, auto_reduce_batch_size=True)",
            "                             output_dir=negative_test_output_dir, auto_reduce_batch_size=True,\n"
            '                             file_names=[uuid.uuid4().hex + ".wav" for i in range(config["n_samples_val"])])',
        )
        .replace(
            '                    self.best_val_accuracy = self.history["val_accuracy"][-1]\n',
            '                    self.best_val_accuracy = self.history["val_accuracy"][-1]\n'
            '                    self.best_val_fp = min(self.best_val_fp, self.history["val_fp_per_hr"][-1])\n',
        )
    )
    monkeypatch.setattr(driver, "TRAIN_SOURCE_SHA256", digest(source))
    monkeypatch.setattr(driver, "TRAIN_PATCHED_SHA256", digest(patched.encode()))
    path = tmp_path / "train.py"
    path.write_bytes(source)

    driver.patch_train(path)

    result = path.read_text()
    assert result.count("default=False,") == 5
    assert result.count('adversarial_texts = list(config["custom_negative_phrases"])') == 2
    assert result.count('n_current_samples < config["n_samples"]') == 2
    assert result.count('n_current_samples < config["n_samples_val"]') == 2
    assert 'opset_version=13, input_names=["x"]' in result
    assert (
        result.count(
            'file_names=[uuid.uuid4().hex + ".wav" for i in range(config["n_samples_val"])]'
        )
        == 2
    )
    assert "best_val_fp = min(self.best_val_fp" in result
    assert digest(path.read_bytes()) == digest(patched.encode())


def test_train_patch_hash_includes_all_restart_and_validation_fixes() -> None:
    driver = load_driver()

    assert driver.TRAIN_PATCHED_SHA256 == (
        "5894e748b57dfa587cfd7517a7ee4bfccda87f8dea2e2546fea1b37b6fcc22bc"
    )


def test_patch_rejects_an_unknown_source(tmp_path: Path) -> None:
    driver = load_driver()
    path = tmp_path / "train.py"
    path.write_text("not the pinned source")

    with pytest.raises(RuntimeError, match="source SHA-256"):
        driver.patch_train(path)


def test_openwakeword_metadata_patch_is_exact_and_gpu_specific(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    source = b"before\n        'onnxruntime>=1.10.0,<2',\nafter\n"
    patched = b"before\n        'onnxruntime-gpu==1.20.0',\nafter\n"
    monkeypatch.setattr(driver, "OWW_SETUP_SOURCE_SHA256", digest(source))
    monkeypatch.setattr(driver, "OWW_SETUP_PATCHED_SHA256", digest(patched))
    path = tmp_path / "setup.py"
    path.write_bytes(source)

    driver.patch_openwakeword_setup(path)

    assert path.read_bytes() == patched


def test_openwakeword_metadata_patch_hashes_are_pinned() -> None:
    driver = load_driver()

    assert driver.OWW_SETUP_SOURCE_SHA256 == (
        "6487c132db5a16b1b45964321bac15cc3d87e23d3bd98edc2f89990a4072a2af"
    )
    assert driver.OWW_SETUP_PATCHED_SHA256 == (
        "8816856e0396bf62460860fe2bd40d0f26d09ece6b1196a5a8e9d6602ca1ac49"
    )


def test_piper_patch_allows_pickle_only_for_verified_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    source = b"torch_model = torch.load(model_path)\n"
    patched = b"torch_model = torch.load(model_path, weights_only=False)\n"
    monkeypatch.setattr(driver, "PIPER_SOURCE_SHA256", digest(source))
    monkeypatch.setattr(driver, "PIPER_PATCHED_SHA256", digest(patched))
    path = tmp_path / "generate_samples.py"
    path.write_bytes(source)

    driver.patch_piper(path)

    assert path.read_bytes() == patched


def test_soundfile_patch_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    driver = load_driver()
    source = """import librosa
import torch
import torchaudio
torchaudio.set_audio_backend("soundfile")
        info = torchaudio.info(file_path)
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
                original_data, _ = torchaudio.load(
                    audio_path,
                    frame_offset=original_sample_offset,
                    num_frames=original_num_samples,
                )
"""
    expected = """import librosa
import soundfile as sf
import torch
import torchaudio
if hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend("soundfile")
        info = sf.info(str(file_path))
        return info.frames, info.samplerate
                original_data, _ = sf.read(
                    audio_path,
                    start=original_sample_offset,
                    frames=original_num_samples,
                    always_2d=True,
                    dtype="float32",
                )
                original_data = torch.from_numpy(original_data.T.copy())
"""
    monkeypatch.setattr(driver, "AUDIO_IO_SOURCE_SHA256", digest(source.encode()))
    monkeypatch.setattr(driver, "AUDIO_IO_PATCHED_SHA256", digest(expected.encode()))
    path = tmp_path / "io.py"
    path.write_text(source)

    driver.patch_audio_io(path)

    assert path.read_text() == expected


def test_prepare_compiles_patched_audio_io_before_runtime_probes() -> None:
    driver = load_driver()
    source = inspect.getsource(driver.prepare)

    patch = source.index("patch_audio_io(Path(audio_io))")
    compile_check = source.index('"py_compile"')
    piper_probe = source.index("_probe_piper_import")
    cuda_probe = source.index("require_training_cuda")

    assert patch < compile_check < piper_probe < cuda_probe


def test_plan_uses_two_venvs_three_training_stages_and_external_conversion(
    tmp_path: Path,
) -> None:
    driver = load_driver()
    workspace = tmp_path / "gi-v3"
    checkpoint_dir = tmp_path / "drive" / "checkpoints"

    plan = driver.build_plan(workspace, checkpoint_dir, CONFIG)

    assert plan["python"] == "3.12.13"
    assert plan["cuda_required"] is True
    assert plan["config"]["sha256"] == driver.CONFIG_SHA256
    assert plan["venvs"] == {
        "training": str(workspace / ".venv-train"),
        "conversion": str(workspace / ".venv-convert"),
    }
    stages = {stage["name"]: stage for stage in plan["stages"]}
    for name, flag in (
        ("generate", "--generate_clips"),
        ("augment", "--augment_clips"),
        ("train", "--train_model"),
    ):
        assert flag in stages[name]["operation"]
        assert stages[name]["command"][-2:] == ["--stage", name]
        assert "--checkpoint-dir" in stages[name]["command"]
        assert stages[name]["checkpoint"].startswith(str(checkpoint_dir))

    conversion = stages["convert"]["operation"]
    assert conversion[0] == str(workspace / ".venv-convert/bin/onnx2tf")
    assert conversion[-6:] == ["-kat", "x", "-ewo", "-efot", "-ens", "32"]
    assert stages["verify"]["limits"] == {
        "input_shape": [1, 16, 96],
        "seeded_samples": 32,
        "max_absolute_error": 1e-5,
        "minimum_cosine_similarity": 0.99999,
    }
    rendered = json.dumps(plan).lower()
    assert "telegram" not in rendered
    assert "human audio" not in rendered
    assert plan["paid_runtime"] is False
    assert plan["dependency_locks"] == driver.LOCK_PROVENANCE


def test_runtime_guard_requires_python_312_and_cuda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver = load_driver()

    monkeypatch.setattr(driver.sys, "version_info", (3, 13, 0))
    with pytest.raises(RuntimeError, match="Python 3.12"):
        driver.require_host_runtime()

    monkeypatch.setattr(driver.sys, "version_info", (3, 12, 12))
    with pytest.raises(RuntimeError, match="3.12.13"):
        driver.require_host_runtime()

    monkeypatch.setattr(driver.sys, "version_info", (3, 12, 13))
    monkeypatch.setattr(driver.shutil, "which", lambda command: None)
    with pytest.raises(RuntimeError, match="CUDA"):
        driver.require_host_runtime()

    assert "CUDAExecutionProvider" in driver.TRAIN_CUDA_PROBE


def test_disk_guard_requires_35_gib_before_downloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    monkeypatch.setattr(
        driver.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=35 * 1024**3 - 1),
    )
    with pytest.raises(RuntimeError, match="35 GiB"):
        driver.require_free_disk(tmp_path)

    monkeypatch.setattr(
        driver.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=35 * 1024**3),
    )
    driver.require_free_disk(tmp_path)


def test_colab_checkpoint_guard_requires_a_mounted_drive(tmp_path: Path) -> None:
    driver = load_driver()
    content = tmp_path / "content"
    drive = content / "drive"
    mydrive = drive / "MyDrive"
    mydrive.mkdir(parents=True)
    checkpoint = mydrive / "gi-v3"

    with pytest.raises(RuntimeError, match="mounted Google Drive"):
        driver.require_checkpoint_storage(
            checkpoint, content_root=content, is_mount=lambda path: False
        )
    driver.require_checkpoint_storage(checkpoint, content_root=content, is_mount=lambda path: True)
    with pytest.raises(RuntimeError, match="MyDrive"):
        driver.require_checkpoint_storage(
            content / "ephemeral", content_root=content, is_mount=lambda path: True
        )


def test_audioset_extractor_is_fixed_to_first_300_embedded_rows() -> None:
    driver = load_driver()
    source = driver.AUDIOSET_EXTRACTOR

    assert "Audio(decode=False)" in source
    assert "range(300)" in source
    assert '["bytes"]' in source
    assert "resample_poly" in source
    assert "16000" in source
    assert "PCM_16" in source
    assert "audioset-manifest.json" in source


def test_parity_verifier_checks_the_pinned_streaming_runtime_boundary() -> None:
    driver = load_driver()
    source = driver.PARITY_VERIFIER

    assert "OpenWakeWord.from_model" in source
    assert "input_windows != 16" in source
    assert "range(15)" in source
    assert "process_streaming" in source
    assert "np.isfinite(maximum)" in source
    assert "np.isfinite(cosine)" in source
    assert '"streaming_first_output_window": 16' in source


def test_manifest_and_lock_plan_keeps_final_artifacts_in_checkpoint_dir(
    tmp_path: Path,
) -> None:
    driver = load_driver()
    plan = driver.build_plan(tmp_path / "work", tmp_path / "checkpoints", CONFIG)
    final = next(stage for stage in plan["stages"] if stage["name"] == "bundle")

    assert final["manifest"].endswith("gi-v3-manifest.json")
    assert final["training_lock"] == str(driver.TRAINING_LOCK)
    assert final["conversion_lock"] == str(driver.CONVERSION_LOCK)
    assert final["training_audit"].endswith("gi-v3-training-freeze.txt")
    assert final["conversion_audit"].endswith("gi-v3-conversion-freeze.txt")
    assert final["checkpoint"].startswith(str(tmp_path / "checkpoints"))


def test_stage_output_validation_checks_exact_counts_and_feature_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    monkeypatch.setattr(
        driver,
        "GENERATED_COUNTS",
        {
            Path("gi-v3-work/gi/positive_train"): 2,
            Path("gi-v3-work/gi/positive_test"): 1,
            Path("gi-v3-work/gi/negative_train"): 2,
            Path("gi-v3-work/gi/negative_test"): 1,
        },
    )
    for relative, count in driver.GENERATED_COUNTS.items():
        directory = tmp_path / relative
        directory.mkdir(parents=True)
        for index in range(count):
            (directory / f"{index}.wav").write_bytes(b"RIFF")
    driver.validate_stage_outputs(tmp_path, "generate")
    (tmp_path / "gi-v3-work/gi/positive_train/0.wav").unlink()
    with pytest.raises(RuntimeError, match="generated WAV count"):
        driver.validate_stage_outputs(tmp_path, "generate")

    monkeypatch.setattr(
        driver,
        "_npy_metadata",
        lambda workspace, paths: {
            str(path): {"shape": list(driver.FEATURE_SHAPES[path]), "dtype": "float32"}
            for path in paths
        },
    )
    driver.validate_stage_outputs(tmp_path, "augment")
    monkeypatch.setattr(
        driver,
        "_npy_metadata",
        lambda workspace, paths: {
            str(path): {"shape": [1, 16, 96], "dtype": "float32"} for path in paths
        },
    )
    with pytest.raises(RuntimeError, match="feature array"):
        driver.validate_stage_outputs(tmp_path, "augment")


def test_onnx_stage_validation_uses_training_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    calls = []
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda command, **kwargs: (
            calls.append((command, kwargs))
            or SimpleNamespace(stdout='{"name": "x", "shape": [1, 16, 96]}\n')
        ),
    )

    assert driver._onnx_metadata(tmp_path, Path("gi-v3-work/gi.onnx")) == {
        "name": "x",
        "shape": [1, 16, 96],
    }

    assert calls[0][0][0] == str(tmp_path / ".venv-train/bin/python")


def test_convert_prepares_venv_and_prepends_its_bin_to_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    checkpoint_dir = tmp_path / "checkpoints"
    onnx = workspace / "gi-v3-work/gi.onnx"
    onnx.parent.mkdir(parents=True)
    onnx.write_bytes(b"onnx")
    events = []

    monkeypatch.setattr(
        driver,
        "validate_stage_outputs",
        lambda work, stage: events.append(("validate", work, stage)),
    )
    monkeypatch.setattr(
        driver,
        "prepare_conversion",
        lambda work, checkpoints: events.append(("prepare", work, checkpoints)),
    )

    def fake_run(command, cwd=None, env=None):
        events.append(("run", list(command), cwd, env))
        output = workspace / "gi-v3-conversion"
        output.mkdir()
        (output / "gi_float32.tflite").write_bytes(b"tflite")
        (output / "gi_accuracy_report.json").write_text("{}")
        (output / "gi_accuracy_comparison_report.json").write_text("{}")

    monkeypatch.setattr(driver, "run", fake_run)

    driver.convert(workspace, checkpoint_dir)

    assert events[0] == ("validate", workspace, "train")
    assert events[1] == ("prepare", workspace, checkpoint_dir)
    conversion = events[2]
    assert conversion[0] == "run"
    assert conversion[3]["PATH"].split(driver.os.pathsep)[0] == str(workspace / ".venv-convert/bin")
    assert (workspace / "gi-v3-work/gi-v3.tflite").read_bytes() == b"tflite"


def test_checkpoint_archive_is_atomic_verified_and_restartable(tmp_path: Path) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    source = workspace / "stage/data.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"restart me")
    checkpoint = tmp_path / "drive/checkpoint.tar"

    driver._archive_checkpoint(checkpoint, workspace, (Path("stage/data.bin"),), "test")

    assert checkpoint.is_file()
    assert not Path(f"{checkpoint}.part").exists()
    assert driver._checkpoint_valid(checkpoint)
    source.unlink()
    driver._restore_checkpoint(checkpoint, workspace)
    assert source.read_bytes() == b"restart me"

    with checkpoint.open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(RuntimeError, match="Invalid checkpoint"):
        driver._restore_checkpoint(checkpoint, workspace)


def test_completed_stage_is_always_restored_from_verified_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    checkpoint_dir = tmp_path / "checkpoints"
    relative = Path("gi-v3-work/gi/positive_train")
    source = workspace / relative
    source.mkdir(parents=True)
    (source / "0.wav").write_bytes(b"verified")
    monkeypatch.setattr(driver, "STAGE_OUTPUTS", {**driver.STAGE_OUTPUTS, "generate": (relative,)})
    monkeypatch.setattr(driver, "GENERATED_COUNTS", {relative: 1})
    checkpoint = driver._checkpoint_path(checkpoint_dir, "generated-clips")
    driver._archive_checkpoint(checkpoint, workspace, (relative,), "generate")
    (source / "0.wav").write_bytes(b"local-corruption-with-the-same-count")
    monkeypatch.setattr(
        driver,
        "_verify_stage_inputs",
        lambda *args: pytest.fail("completed checkpoint must not rerun the stage"),
    )

    driver.run_training_stage(workspace, checkpoint_dir, "generate")

    assert (source / "0.wav").read_bytes() == b"verified"


def test_checkpoint_sidecar_rejects_wrong_config_provenance(tmp_path: Path) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    source = workspace / "stage/data.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"data")
    checkpoint = tmp_path / "checkpoint.tar"
    driver._archive_checkpoint(checkpoint, workspace, (Path("stage/data.bin"),), "test")
    sidecar = driver._checkpoint_manifest(checkpoint)
    record = json.loads(sidecar.read_text())
    assert record["dependency_locks"] == driver.LOCK_PROVENANCE
    assert record["driver_sha256"] == driver.sha256(driver.DRIVER)
    record["config_sha256"] = "0" * 64
    sidecar.write_text(json.dumps(record))

    assert not driver._checkpoint_valid(checkpoint, "test")


def test_checkpoint_rejects_a_different_driver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    source = workspace / "stage/data.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"data")
    checkpoint = tmp_path / "checkpoint.tar"
    driver._archive_checkpoint(checkpoint, workspace, (Path("stage/data.bin"),), "test")
    changed_driver = tmp_path / "train_gi_v3_colab.py"
    changed_driver.write_bytes(b"changed driver")
    monkeypatch.setattr(driver, "DRIVER", changed_driver)

    assert not driver._checkpoint_valid(checkpoint, "test")


def test_environment_provenance_claims_exact_hash_lock_replay() -> None:
    driver = load_driver()

    assert driver._environment_provenance() == {
        "kind": "checked-in hash locks plus verified direct artifacts",
        "exact_first_install_replay": True,
        "python": "3.12.13",
        "dependency_locks": driver.LOCK_PROVENANCE,
        "audit_snapshots": (
            "gi-v3-training-freeze.txt",
            "gi-v3-conversion-freeze.txt",
        ),
    }


def test_final_manifest_requires_verified_stage_checkpoint_records(tmp_path: Path) -> None:
    driver = load_driver()
    workspace = tmp_path / "work"
    checkpoint_dir = tmp_path / "checkpoints"
    output = workspace / "stage/data"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"stage")
    for stage, name in (
        ("generate", "generated-clips"),
        ("augment", "features"),
        ("train", "onnx"),
    ):
        driver._archive_checkpoint(
            driver._checkpoint_path(checkpoint_dir, name),
            workspace,
            (Path("stage/data"),),
            stage,
        )

    records = driver._stage_checkpoint_records(checkpoint_dir)

    assert set(records) == {"generate", "augment", "train"}
    assert all(record["config_sha256"] == driver.CONFIG_SHA256 for record in records.values())
    bad = driver._checkpoint_manifest(driver._checkpoint_path(checkpoint_dir, "features"))
    record = json.loads(bad.read_text())
    record["config_sha256"] = "0" * 64
    bad.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match="stage checkpoint"):
        driver._stage_checkpoint_records(checkpoint_dir)


def test_train_checkpoint_includes_external_onnx_data(tmp_path: Path) -> None:
    driver = load_driver()
    onnx = tmp_path / "gi-v3-work/gi.onnx"
    external = tmp_path / "gi-v3-work/gi.onnx.data"
    onnx.parent.mkdir(parents=True)
    onnx.write_bytes(b"onnx")
    external.write_bytes(b"weights")

    assert driver._stage_archive_outputs(tmp_path, "train") == (
        Path("gi-v3-work/gi.onnx"),
        Path("gi-v3-work/gi.onnx.data"),
    )
    external.unlink()
    assert driver._stage_archive_outputs(tmp_path, "train") == (Path("gi-v3-work/gi.onnx"),)


def test_final_bundle_includes_all_three_verified_patched_sources(tmp_path: Path) -> None:
    driver = load_driver()
    artifacts = driver._bundle_artifacts(tmp_path / "work", tmp_path / "checkpoints")

    assert (
        artifacts["patched-sources/openwakeword-train.py"]
        .as_posix()
        .endswith("openwakeword/openwakeword/train.py")
    )
    assert (
        artifacts["patched-sources/piper-generate_samples.py"]
        .as_posix()
        .endswith("piper-sample-generator/generate_samples.py")
    )
    assert (
        artifacts["patched-sources/torch-audiomentations-io.py"]
        .as_posix()
        .endswith(".venv-train/lib/python3.12/site-packages/torch_audiomentations/utils/io.py")
    )
    assert artifacts["conversion/gi_accuracy_report.json"] == (
        tmp_path / "work/gi-v3-conversion/gi_accuracy_report.json"
    )
    assert artifacts["conversion/gi_accuracy_comparison_report.json"] == (
        tmp_path / "work/gi-v3-conversion/gi_accuracy_comparison_report.json"
    )
    assert artifacts["locks/gi-v3-training.lock"] == driver.TRAINING_LOCK
    assert artifacts["locks/gi-v3-conversion.lock"] == driver.CONVERSION_LOCK
    assert artifacts["workflow/train_gi_v3_colab.py"] == driver.DRIVER
    assert (
        artifacts["patched-sources/openwakeword-setup.py"]
        .as_posix()
        .endswith("openwakeword/setup.py")
    )


def test_audioset_extract_manifest_verifies_every_wav(tmp_path: Path) -> None:
    driver = load_driver()
    output = tmp_path / "audioset_16k"
    output.mkdir()
    files = []
    for index in range(300):
        path = output / f"{index:04d}.wav"
        path.write_bytes(f"wav-{index}".encode())
        files.append(
            {"file": path.name, "bytes": path.stat().st_size, "sha256": driver.sha256(path)}
        )
    (output / "audioset-manifest.json").write_text(
        json.dumps(
            {
                "source": "audioset-balanced-00.parquet",
                "source_bytes": driver.DOWNLOADS["audioset"].size,
                "source_sha256": driver.DOWNLOADS["audioset"].sha256,
                "rows": 300,
                "files": files,
            }
        )
    )

    driver.verify_audioset_extract(output)

    (output / "0042.wav").write_bytes(b"corrupt")
    with pytest.raises(RuntimeError, match="AudioSet WAV"):
        driver.verify_audioset_extract(output)


def test_rir_verification_checks_lfs_and_clean_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    source = tmp_path / "rir"
    wavs = source / "16khz"
    wavs.mkdir(parents=True)
    for index in range(271):
        (wavs / f"{index}.wav").write_bytes(b"RIFF")
    commands = []
    monkeypatch.setattr(
        driver,
        "run",
        lambda command, cwd=None, env=None: commands.append((list(command), cwd)),
    )
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda command, **kwargs: SimpleNamespace(
            stdout=driver.REVISIONS["rir"] if command[:3] == ["git", "rev-parse", "HEAD"] else ""
        ),
    )

    driver.verify_rir_checkout(source)

    assert (["git", "lfs", "fsck"], source) in commands
    assert (["git", "diff", "--exit-code"], source) in commands


def test_patched_source_checkout_rejects_untracked_or_unknown_changes(tmp_path: Path) -> None:
    driver = load_driver()
    repository = tmp_path / "source"
    repository.mkdir()
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=repository, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    tracked = repository / "train.py"
    tracked.write_text("original\n")
    subprocess.run(["git", "add", "train.py"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=repository, check=True)
    tracked.write_text("patched\n")

    driver.verify_patched_checkout(repository, {Path("train.py"): digest(b"patched\n")})

    (repository / "extra.py").write_text("unknown\n")
    with pytest.raises(RuntimeError, match="dirty source checkout"):
        driver.verify_patched_checkout(repository, {Path("train.py"): digest(b"patched\n")})


def test_patched_source_checkout_rejects_the_wrong_revision(tmp_path: Path) -> None:
    driver = load_driver()
    repository = tmp_path / "source"
    repository.mkdir()
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=repository, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    source = repository / "train.py"
    source.write_text("source\n")
    subprocess.run(["git", "add", "train.py"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=repository, check=True)

    with pytest.raises(RuntimeError, match="revision"):
        driver.verify_patched_checkout(
            repository,
            {Path("train.py"): digest(b"source\n")},
            "0" * 40,
        )


def test_openwakeword_checkout_allows_only_verified_downloaded_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    driver = load_driver()
    repository = tmp_path / "openwakeword"
    repository.mkdir()
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=repository, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    train = repository / "openwakeword/train.py"
    train.parent.mkdir()
    train.write_text("original\n")
    setup = repository / "setup.py"
    setup.write_text("original\n")
    subprocess.run(["git", "add", "openwakeword/train.py", "setup.py"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=repository, check=True)
    train.write_text("patched\n")
    setup.write_text("patched setup\n")
    monkeypatch.setattr(driver, "TRAIN_PATCHED_SHA256", digest(b"patched\n"))
    monkeypatch.setattr(driver, "OWW_SETUP_PATCHED_SHA256", digest(b"patched setup\n"))

    resources = repository / "openwakeword/resources/models"
    resources.mkdir(parents=True)
    for name in (
        "embedding_onnx",
        "embedding_tflite",
        "melspectrogram_onnx",
        "melspectrogram_tflite",
    ):
        asset = driver.DOWNLOADS[name]
        data = f"{name}\n".encode()
        monkeypatch.setitem(
            driver.DOWNLOADS,
            name,
            driver.Download(asset.url, asset.filename, len(data), digest(data)),
        )
        (resources / asset.filename).write_bytes(data)

    driver.verify_patched_checkout(repository, driver._openwakeword_allowed_files())

    (resources / "unexpected.onnx").write_bytes(b"unexpected")
    with pytest.raises(RuntimeError, match="dirty source checkout"):
        driver.verify_patched_checkout(repository, driver._openwakeword_allowed_files())


def test_piper_import_probe_executes_the_patched_generator() -> None:
    driver = load_driver()
    commands = []
    driver.run = lambda command, cwd=None, env=None: commands.append(list(command))

    driver._probe_piper_import(Path("/venv/python"), Path("/src/generate_samples.py"))

    assert commands[0][0] == "/venv/python"
    assert commands[0][-1] == "/src/generate_samples.py"
    assert "exec_module" in commands[0][2]
