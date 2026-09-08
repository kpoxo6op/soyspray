import importlib.util
from pathlib import Path


def load_backup():
    path = Path("apps/recovery-input-backup/backup.py")
    spec = importlib.util.spec_from_file_location("recovery_input_backup", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stable_models_are_seeded_from_the_live_immutable_models(tmp_path, monkeypatch):
    backup = load_backup()
    models = {name: b"1234TFL3" + name.encode() for name in backup.MODELS}
    backup.MODELS = {
        name: (configmap, backup.hashlib.sha256(models[name]).hexdigest())
        for name, (configmap, _) in backup.MODELS.items()
    }
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        backup,
        "live_model",
        lambda configmap: models[
            next(name for name, (candidate, _) in backup.MODELS.items() if candidate == configmap)
        ],
    )

    directory, hashes = backup.stable_models(seed=True)

    assert directory.stat().st_mode & 0o777 == 0o700
    assert {path.name for path in directory.iterdir()} == set(models)
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in directory.iterdir())
    assert all(set(value) == {"active", "stable"} for value in hashes.values())
