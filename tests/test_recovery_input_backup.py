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


def test_new_private_inputs_are_restored_with_original_checksums(tmp_path, monkeypatch):
    # A newly added Vault must be covered automatically. Model seeding does not
    # exercise collection of credentials, inventory identities or nested files.
    backup = load_backup()
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    sources = {
        home / ".config/soyspray/recovery/new/nested.vault.yml": b"encrypted-new-input",
        home / ".config/soyspray/recovery/vault-password": b"dummy-unlock",
        repo / "inventory/soycluster/credentials/certificate_key": b"dummy-identity",
        home / ".kube/config": b"clusters: []\nusers: []\n",
        home / ".ssh/config": b"Host *\n",
        home / ".ssh/known_hosts": b"dummy-host-identity",
        home / ".ssh/id_rsa": b"dummy-ssh-key",
        home / ".aws/config": b"[profile example]\n",
        home / ".aws/login/cache/ignored": b"reproducible-cache",
    }
    for path, content in sources.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(backup, "ROOT", repo)
    monkeypatch.delenv("KUBECONFIG", raising=False)
    monkeypatch.setattr(
        backup.subprocess, "check_output", lambda *a, **kw: f"identityfile {home}/.ssh/id_rsa\n"
    )
    originals = backup.local_inputs()
    hashes = backup.stage_local_inputs(tmp_path / "staged", originals)
    assert "recovery/new/nested.vault.yml" in hashes
    assert set(originals.values()) == set(sources) - {home / ".aws/login/cache/ignored"}
    for name, source in originals.items():
        staged = tmp_path / "staged/local" / name
        assert backup.digest(staged) == backup.digest(source) == hashes[name]
        assert staged.stat().st_mode & 0o777 == 0o600
    (home / ".config/soyspray/recovery/escape").symlink_to(home / ".ssh/id_rsa")
    import pytest

    with pytest.raises(ValueError, match="unexpected symlink"):
        backup.local_inputs()
