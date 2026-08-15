from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gi_v4_synthesize.py"


def _load_module() -> ModuleType:
    assert SCRIPT.is_file(), "missing GI V4 planned-audio renderer"
    spec = importlib.util.spec_from_file_location("gi_v4_synthesize", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


class FakePlanAPI:
    def __init__(self) -> None:
        self.verified: list[object] = []

    def verify_plan(self, plan: object) -> None:
        self.verified.append(plan)

    def canonical_json(self, plan: object) -> bytes:
        self.verify_plan(plan)
        return (
            json.dumps(plan, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()
            + b"\n"
        )


class FakeGenerator:
    PLANNED_NOISE_INTERFACE = 1

    def __init__(self, fail_call: int | None = None) -> None:
        self.load_calls: list[tuple[Path, Path]] = []
        self.batch_calls: list[dict[str, object]] = []
        self.fail_call = fail_call

    def load_planned_model(self, *, model_path: Path, config_path: Path) -> object:
        self.load_calls.append((model_path, config_path))
        return object()

    def generate_planned_batch(
        self,
        renderer: object,
        *,
        texts: list[str],
        speaker_pairs: list[tuple[int, int]],
        slerp_weight: float,
        length_scale: float,
        noise_scale: float,
        noise_scale_w: float,
        duration_noise_seeds: list[int],
        latent_noise_seeds: list[int],
    ) -> list[bytes]:
        call = {
            "renderer": renderer,
            "texts": texts,
            "speaker_pairs": speaker_pairs,
            "slerp_weight": slerp_weight,
            "length_scale": length_scale,
            "noise_scale": noise_scale,
            "noise_scale_w": noise_scale_w,
            "duration_noise_seeds": duration_noise_seeds,
            "latent_noise_seeds": latent_noise_seeds,
        }
        self.batch_calls.append(call)
        if self.fail_call == len(self.batch_calls):
            raise RuntimeError("simulated interrupted renderer")
        return [((seed % 30_000) + 1).to_bytes(2, "little") * 80 for seed in latent_noise_seeds]


def _record(
    index: int,
    partition: str,
    class_name: str,
    text: str,
    speakers: list[int],
    seed: int,
    *,
    slerp_weight: float = 0.0,
) -> dict[str, object]:
    return {
        "index": index,
        "filename": f"{index:08d}.wav",
        "partition": partition,
        "class": class_name,
        "text": text,
        "source": "piper_fixed",
        "speakers": speakers,
        "slerp_weight": slerp_weight,
        "length_scale": 0.75,
        "noise_scale": 0.98 if partition == "train" else 1.0,
        "noise_scale_w": 0.98 if partition == "train" else 1.0,
        "seed": seed,
    }


def _plan(checkpoint_sha256: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "human_audio_used": False,
        "piper": {
            "checkpoint_filename": "en_US-libritts_r-medium.pt",
            "checkpoint_sha256": checkpoint_sha256,
            "num_speakers": 904,
        },
        "records": [
            _record(0, "train", "positive", "GI", [1, 2], 11),
            _record(1, "train", "positive", "gee eye", [3, 4], 12, slerp_weight=0.5),
            _record(2, "train", "positive", "GI", [5, 6], 13),
            _record(3, "train", "negative", "nabu", [7, 8], 21),
            _record(4, "val", "positive", "gee eye", [101, 102], 31),
            _record(5, "val", "negative", "okay nabu", [103, 104], 41),
            _record(6, "train", "positive", "GI", [9, 10], 22),
        ],
    }


def _sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    model = tmp_path / "en_US-libritts_r-medium.pt"
    config = Path(f"{model}.json")
    generator = tmp_path / "generate_samples.py"
    model.write_bytes(b"pinned fake model")
    config.write_text('{"pinned":"fake config"}\n')
    generator.write_text("# pinned fake planned generator\n")
    return model, config, generator


def _render(
    module: ModuleType,
    tmp_path: Path,
    fake: FakeGenerator | object,
) -> tuple[dict[str, object], Path, FakePlanAPI, Path, Path, Path]:
    model, config, generator = _sources(tmp_path)
    plan = _plan(_sha256(model))
    output = tmp_path / "gi-v4-work"
    plan_api = FakePlanAPI()
    manifest = module.render_stage(
        plan,
        output,
        model,
        generator,
        expected_generator_sha256=_sha256(generator),
        batch_size=2,
        _plan_api=plan_api,
        _generator_module=fake,
        _expected_config_sha256=_sha256(config),
    )
    return manifest, output, plan_api, model, config, generator


def test_render_groups_fixed_batches_and_promotes_only_verified_tree(tmp_path: Path) -> None:
    module = _load_module()
    fake = FakeGenerator()
    stale = tmp_path / "gi-v4-work.part" / "stale.txt"
    stale.parent.mkdir()
    stale.write_text("old partial generation")

    manifest, output, plan_api, model, config, _ = _render(module, tmp_path, fake)

    assert plan_api.verified
    assert fake.load_calls == [(model, config)]
    assert len(fake.batch_calls) == 6
    assert fake.batch_calls[0]["texts"] == ["GI", "GI"]
    assert fake.batch_calls[0]["speaker_pairs"] == [(1, 2), (5, 6)]
    assert fake.batch_calls[0]["duration_noise_seeds"] == [
        6_300_434_847_001_554_600,
        8_455_171_084_186_682_895,
    ]
    assert fake.batch_calls[0]["latent_noise_seeds"] == [
        6_281_845_710_932_414_759,
        5_131_803_902_315_117_104,
    ]
    assert fake.batch_calls[1]["texts"] == ["GI"]
    assert fake.batch_calls[2]["texts"] == ["gee eye"]
    assert not Path(f"{output}.part").exists()
    assert not stale.exists()

    expected = {
        "gi/positive_train/00000000.wav",
        "gi/positive_train/00000001.wav",
        "gi/positive_train/00000002.wav",
        "gi/negative_train/00000003.wav",
        "gi/positive_test/00000004.wav",
        "gi/negative_test/00000005.wav",
        "gi/positive_train/00000006.wav",
    }
    actual = {path.relative_to(output).as_posix() for path in output.rglob("*.wav")}
    assert actual == expected
    assert not list(output.rglob("*.part"))
    assert manifest["human_audio_used"] is False
    assert [record["seed"] for record in manifest["records"]] == [11, 12, 13, 21, 31, 41, 22]
    assert [record["speakers"] for record in manifest["records"]] == [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
        [101, 102],
        [103, 104],
        [9, 10],
    ]
    assert json.loads((output / "gi-v4-generated-manifest.json").read_text()) == manifest
    assert (output / "gi-v4-synthesis-plan.json").is_file()
    module.verify_generated_stage(
        _plan(_sha256(model)), output, manifest["piper"], _plan_api=plan_api
    )


def test_interrupted_tree_is_not_published_and_next_run_restarts(tmp_path: Path) -> None:
    module = _load_module()
    failing = FakeGenerator(fail_call=2)
    model, config, generator = _sources(tmp_path)
    plan = _plan(_sha256(model))
    output = tmp_path / "gi-v4-work"
    kwargs = {
        "expected_generator_sha256": _sha256(generator),
        "batch_size": 2,
        "_plan_api": FakePlanAPI(),
        "_expected_config_sha256": _sha256(config),
    }

    with pytest.raises(RuntimeError, match="simulated interrupted renderer"):
        module.render_stage(plan, output, model, generator, _generator_module=failing, **kwargs)

    assert not output.exists()
    part = Path(f"{output}.part")
    assert part.is_dir()
    sentinel = part / "must-not-be-resumed"
    sentinel.write_text("stale")

    succeeding = FakeGenerator()
    module.render_stage(plan, output, model, generator, _generator_module=succeeding, **kwargs)

    assert not sentinel.exists()
    assert succeeding.batch_calls[0]["texts"] == ["GI", "GI"]
    assert len(list(output.rglob("*.wav"))) == len(plan["records"])


def test_old_piper_helper_fails_before_model_load_or_output(tmp_path: Path) -> None:
    module = _load_module()
    model, config, generator = _sources(tmp_path)
    plan = _plan(_sha256(model))
    output = tmp_path / "gi-v4-work"

    class OldGenerator:
        def generate_samples(self, **kwargs: object) -> None:
            raise AssertionError(kwargs)

    with pytest.raises(
        RuntimeError,
        match="duration_noise_seeds.*latent_noise_seeds",
    ):
        module.render_stage(
            plan,
            output,
            model,
            generator,
            expected_generator_sha256=_sha256(generator),
            _plan_api=FakePlanAPI(),
            _generator_module=OldGenerator(),
            _expected_config_sha256=_sha256(config),
        )

    assert not output.exists()
    assert not Path(f"{output}.part").exists()


@pytest.mark.parametrize("target", ["checkpoint", "config", "generator"])
def test_pinned_sources_are_checked_before_model_load(tmp_path: Path, target: str) -> None:
    module = _load_module()
    fake = FakeGenerator()
    model, config, generator = _sources(tmp_path)
    plan = _plan(_sha256(model))
    expected_generator_sha256 = _sha256(generator)
    expected_config_sha256 = _sha256(config)
    {"checkpoint": model, "config": config, "generator": generator}[target].write_bytes(b"tampered")

    with pytest.raises(RuntimeError, match="Unexpected pinned Piper"):
        module.render_stage(
            plan,
            tmp_path / "gi-v4-work",
            model,
            generator,
            expected_generator_sha256=expected_generator_sha256,
            _plan_api=FakePlanAPI(),
            _generator_module=fake,
            _expected_config_sha256=expected_config_sha256,
        )

    assert fake.load_calls == []


@pytest.mark.parametrize("target", ["wav", "extra", "manifest", "plan"])
def test_verification_rejects_file_manifest_and_plan_tampering(tmp_path: Path, target: str) -> None:
    module = _load_module()
    manifest, output, plan_api, model, _, _ = _render(module, tmp_path, FakeGenerator())
    plan = _plan(_sha256(model))
    if target == "wav":
        with (output / manifest["records"][0]["file"]).open("ab") as wav_file:
            wav_file.write(b"tampered")
    elif target == "extra":
        (output / "gi/positive_train/extra.wav").write_bytes(b"extra")
    elif target == "manifest":
        damaged = copy.deepcopy(manifest)
        damaged["records"][0]["text"] = "nabu"
        (output / "gi-v4-generated-manifest.json").write_text(json.dumps(damaged))
    else:
        plan["records"][0]["text"] = "nabu"

    with pytest.raises(RuntimeError):
        module.verify_generated_stage(plan, output, manifest["piper"], _plan_api=plan_api)
