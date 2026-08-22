"""Checks for the GI v3 manual browser checkpoint helper."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/gi_v3_browser_checkpoints.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("gi_v3_browser_checkpoints", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_checkpoint(helper, checkpoint_dir: Path, stage: str, payload: bytes) -> Path:
    workspace = checkpoint_dir.parent / f"workspace-{stage}"
    source = (
        workspace / "gi-v3-manifest.json"
        if stage == "finish"
        else workspace / f"output-{stage}.bin"
    )
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    if stage == "finish":
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "gi-v3-manifest.json").write_bytes(payload)
    archive = checkpoint_dir / helper.STAGES[stage].archive
    helper.TRAINER._archive_checkpoint(
        archive,
        workspace,
        (source.relative_to(workspace),),
        helper.STAGES[stage].trainer_stage,
    )
    return archive


def rewrite_sha256sums(path: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        data = (path.parent / name).read_bytes()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
    path.write_text("".join(lines))


def test_part_size_and_stage_allowlist_are_fixed() -> None:
    helper = load_helper()

    assert helper.CHUNK_BYTES == 64 * 1024**2
    assert tuple(helper.STAGES) == ("generate", "augment", "train", "finish")
    assert [helper.STAGES[name].archive for name in helper.STAGES] == [
        "gi-v3-generated-clips.tar",
        "gi-v3-features.tar",
        "gi-v3-onnx.tar",
        "gi-v3-final-bundle.tar",
    ]


def test_pack_and_restore_three_cumulative_verified_checkpoints(tmp_path: Path) -> None:
    helper = load_helper()
    source_checkpoints = tmp_path / "source-checkpoints"
    transfers = tmp_path / "transfers"
    restored = tmp_path / "restored"

    for index, stage in enumerate(("generate", "augment", "train"), start=1):
        make_checkpoint(helper, source_checkpoints, stage, bytes(range(index * 5)))
        helper.pack_checkpoint(stage, source_checkpoints, transfers, chunk_bytes=4)

    assert helper.restore_through("train", restored, transfers) == (
        "generate",
        "augment",
        "train",
    )
    for stage in ("generate", "augment", "train"):
        archive = restored / helper.STAGES[stage].archive
        assert helper.TRAINER._checkpoint_valid(archive, helper.STAGES[stage].trainer_stage)
        manifest = transfers / helper.STAGES[stage].transfer_manifest
        entries = helper.read_sha256sums(manifest)
        parts = [name for name in entries if ".part-" in name]
        assert parts == [
            f"{helper.STAGES[stage].archive}.part-{number:04d}" for number in range(len(parts))
        ]


def test_corrupt_part_is_rejected_before_checkpoint_publication(tmp_path: Path) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    restored = tmp_path / "restored"
    make_checkpoint(helper, source, "generate", b"verified checkpoint")
    helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)
    next(transfers.glob("gi-v3-generated-clips.tar.part-*")).write_bytes(b"tampered")

    with pytest.raises(RuntimeError, match="SHA-256"):
        helper.restore_through("generate", restored, transfers)

    assert not (restored / helper.STAGES["generate"].archive).exists()


def test_manifest_path_traversal_is_rejected(tmp_path: Path) -> None:
    helper = load_helper()
    transfers = tmp_path / "transfers"
    transfers.mkdir()
    manifest = transfers / helper.STAGES["generate"].transfer_manifest
    manifest.write_text(f"{'0' * 64}  ../human.wav\n")

    with pytest.raises(RuntimeError, match="safe basename"):
        helper.restore_through("generate", tmp_path / "restored", transfers)

    assert not (tmp_path / "human.wav").exists()


@pytest.mark.parametrize("part_names", [["part-0001"], ["part-0000", "part-0002"]])
def test_missing_or_nonconsecutive_parts_are_rejected(
    tmp_path: Path, part_names: list[str]
) -> None:
    helper = load_helper()
    transfers = tmp_path / "transfers"
    transfers.mkdir()
    spec = helper.STAGES["generate"]
    sidecar = transfers / f"{spec.archive}.json"
    sidecar.write_text("{}")
    names = [sidecar.name]
    for suffix in part_names:
        part = transfers / f"{spec.archive}.{suffix}"
        part.write_bytes(suffix.encode())
        names.append(part.name)
    manifest = transfers / spec.transfer_manifest
    rewrite_sha256sums(manifest, names)

    with pytest.raises(RuntimeError, match="consecutive"):
        helper.restore_through("generate", tmp_path / "restored", transfers)


@pytest.mark.parametrize("unsafe_name", ["human.wav", "unexpected.bin"])
def test_human_audio_and_unknown_files_are_rejected(tmp_path: Path, unsafe_name: str) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    make_checkpoint(helper, source, "generate", b"checkpoint")
    helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)
    (transfers / unsafe_name).write_bytes(b"private")

    with pytest.raises(RuntimeError, match="Unexpected transfer file"):
        helper.restore_through("generate", tmp_path / "restored", transfers)


def test_symlinked_transfer_file_is_rejected(tmp_path: Path) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    make_checkpoint(helper, source, "generate", b"checkpoint")
    helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)
    part = next(transfers.glob("gi-v3-generated-clips.tar.part-*"))
    target = tmp_path / "outside-part"
    part.replace(target)
    part.symlink_to(target)

    with pytest.raises(RuntimeError, match="symlink"):
        helper.restore_through("generate", tmp_path / "restored", transfers)


def test_pack_rejects_temp_symlink_without_touching_target(tmp_path: Path) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    transfers.mkdir()
    make_checkpoint(helper, source, "generate", b"checkpoint")
    outside = tmp_path / "outside"
    outside.write_bytes(b"keep")
    (transfers / "gi-v3-generated-clips.tar.json.part").symlink_to(outside)

    with pytest.raises(RuntimeError, match="symlink"):
        helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)

    assert outside.read_bytes() == b"keep"


def test_repack_failure_preserves_existing_valid_transfer(tmp_path: Path) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    make_checkpoint(helper, source, "generate", b"first checkpoint")
    helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)
    before = {path.name: helper.sha256(path) for path in transfers.iterdir()}

    workspace = tmp_path / "replacement-workspace"
    output = workspace / "replacement.bin"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"different checkpoint")
    helper.TRAINER._archive_checkpoint(
        source / helper.STAGES["generate"].archive,
        workspace,
        (output.relative_to(workspace),),
        "generate",
    )

    with pytest.raises(RuntimeError, match="preserve it"):
        helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)

    assert {path.name: helper.sha256(path) for path in transfers.iterdir()} == before


def test_different_trainer_driver_rejects_restored_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    restored = tmp_path / "restored"
    make_checkpoint(helper, source, "generate", b"checkpoint")
    helper.pack_checkpoint("generate", source, transfers, chunk_bytes=4)
    changed_driver = tmp_path / "train_gi_v3_colab.py"
    changed_driver.write_text("changed")
    monkeypatch.setattr(helper.TRAINER, "DRIVER", changed_driver)

    with pytest.raises(RuntimeError, match="trainer provenance"):
        helper.restore_through("generate", restored, transfers)

    assert not (restored / helper.STAGES["generate"].archive).exists()


def test_finish_restore_retry_restores_separate_manifest(tmp_path: Path) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    restored = tmp_path / "restored"
    for stage in helper.STAGES:
        payload = b'{"model":"gi-v3"}\n' if stage == "finish" else stage.encode()
        make_checkpoint(helper, source, stage, payload)
        helper.pack_checkpoint(stage, source, transfers, chunk_bytes=4)

    helper.restore_through("finish", restored, transfers)
    manifest = restored / "gi-v3-manifest.json"
    manifest.unlink()

    helper.restore_through("finish", restored, transfers)

    assert manifest.read_text() == '{"model":"gi-v3"}\n'


def test_finish_manifest_restore_replaces_symlink_without_following_it(
    tmp_path: Path,
) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    transfers = tmp_path / "transfers"
    restored = tmp_path / "restored"
    for stage in helper.STAGES:
        payload = b'{"model":"gi-v3"}\n' if stage == "finish" else stage.encode()
        make_checkpoint(helper, source, stage, payload)
        helper.pack_checkpoint(stage, source, transfers, chunk_bytes=4)
    restored.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"keep")
    (restored / "gi-v3-manifest.json").symlink_to(outside)

    helper.restore_through("finish", restored, transfers)

    assert outside.read_bytes() == b"keep"
    assert not (restored / "gi-v3-manifest.json").is_symlink()


def test_finish_restore_rejects_corrupt_manifest_without_import_copy(
    tmp_path: Path,
) -> None:
    helper = load_helper()
    checkpoints = tmp_path / "checkpoints"
    for stage in helper.STAGES:
        make_checkpoint(helper, checkpoints, stage, stage.encode())
    manifest = checkpoints / "gi-v3-manifest.json"
    manifest.write_text('{"model":"gi-v3"}\n')
    workspace = tmp_path / "bundle-workspace"
    bundled = workspace / "gi-v3-manifest.json"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(manifest.read_bytes())
    helper.TRAINER._archive_checkpoint(
        checkpoints / helper.STAGES["finish"].archive,
        workspace,
        (bundled.relative_to(workspace),),
        "bundle",
    )
    manifest.write_text("corrupt\n")

    with pytest.raises(RuntimeError, match="Missing transfer file"):
        helper.restore_through("finish", checkpoints, tmp_path / "empty-import")


@pytest.mark.parametrize("link_name", ["archive", "sidecar"])
def test_restore_rejects_symlinked_existing_checkpoint(tmp_path: Path, link_name: str) -> None:
    helper = load_helper()
    source = tmp_path / "source"
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    archive = make_checkpoint(helper, source, "generate", b"checkpoint")
    sidecar = helper.TRAINER._checkpoint_manifest(archive)
    if link_name == "archive":
        (checkpoint_dir / archive.name).symlink_to(archive)
        (checkpoint_dir / sidecar.name).write_bytes(sidecar.read_bytes())
    else:
        (checkpoint_dir / archive.name).write_bytes(archive.read_bytes())
        (checkpoint_dir / sidecar.name).symlink_to(sidecar)

    with pytest.raises(RuntimeError, match="symlinked generate checkpoint"):
        helper.restore_through("generate", checkpoint_dir, tmp_path / "empty-import")


def test_live_paths_are_exact_and_reject_symlinks(tmp_path: Path) -> None:
    helper = load_helper()
    content = tmp_path / "content"
    content.mkdir()
    exact = {
        "workspace": content / "gi-v3",
        "checkpoint_dir": content / "gi-v3-checkpoints",
        "import_dir": content / "gi-v3-import",
        "transfer_dir": content / "gi-v3-transfer",
    }

    helper.require_local_boundaries(content_root=content, **exact)
    with pytest.raises(RuntimeError, match="must be"):
        helper.require_local_boundaries(
            content_root=content,
            **{**exact, "checkpoint_dir": content / "other"},
        )

    outside = tmp_path / "outside"
    outside.mkdir()
    exact["import_dir"].symlink_to(outside)
    with pytest.raises(RuntimeError, match="symlink"):
        helper.require_local_boundaries(content_root=content, **exact)


def test_cli_has_run_pack_and_restore_commands() -> None:
    helper = load_helper()
    parser = helper.build_parser()

    assert parser.parse_args(["pack", "--stage", "generate"]).command == "pack"
    assert parser.parse_args(["restore", "--through", "train"]).command == "restore"
    assert parser.parse_args(["run", "--target", "finish"]).command == "run"


def test_run_uses_existing_trainer_stage_and_packs_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_helper()
    workspace = tmp_path / "workspace"
    checkpoints = tmp_path / "checkpoints"
    transfers = tmp_path / "transfers"
    events = []

    monkeypatch.setattr(helper.TRAINER, "require_host_runtime", lambda: events.append("runtime"))
    monkeypatch.setattr(
        helper.TRAINER,
        "prepare",
        lambda work, checkpoint_dir, config: events.append(
            ("prepare", work, checkpoint_dir, config)
        ),
    )

    def fake_stage(work: Path, checkpoint_dir: Path, stage: str) -> None:
        events.append(("stage", stage))
        make_checkpoint(helper, checkpoint_dir, stage, b"generated")

    monkeypatch.setattr(helper.TRAINER, "run_training_stage", fake_stage)

    helper.run_target("generate", workspace, checkpoints, tmp_path / "imports", transfers)

    assert events[0] == "runtime"
    assert events[1][0] == "prepare"
    assert events[2] == ("stage", "generate")
    assert (transfers / helper.STAGES["generate"].transfer_manifest).is_file()


def test_run_stops_before_prepare_without_prior_durable_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_helper()
    monkeypatch.setattr(
        helper.TRAINER,
        "prepare",
        lambda *args: pytest.fail("prepare must wait for the prior checkpoint"),
    )

    with pytest.raises(RuntimeError, match="verified generate checkpoint"):
        helper.run_target(
            "augment",
            tmp_path / "workspace",
            tmp_path / "checkpoints",
            tmp_path / "imports",
            tmp_path / "transfers",
        )


def test_cli_provenance_reports_helper_and_trainer_hashes() -> None:
    helper = load_helper()

    record = helper.provenance()

    assert record == {
        "helper_sha256": helper.sha256(SCRIPT),
        "trainer_sha256": helper.sha256(helper.TRAINER.DRIVER),
    }
