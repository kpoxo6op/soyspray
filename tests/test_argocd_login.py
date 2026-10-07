"""Protect the private credential at the actual child-process boundary."""

import json
import sys
from datetime import datetime, timezone

import bcrypt
import pytest
import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

from scripts import argocd_admin_vault, argocd_login


def test_login_sends_only_terminal_input_and_suppresses_output(tmp_path, capsys):
    # A CLI or terminal regression could expose the credential in argv, env or
    # stdout. Inventory and manifest tests cannot exercise this process boundary.
    record = tmp_path / "record.json"
    binary = tmp_path / "cli"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys,termios\n"
        "assert not termios.tcgetattr(0)[3] & termios.ECHO\n"
        "print('Password: ',end='',flush=True)\n"
        "value=sys.stdin.readline().rstrip('\\n')\n"
        f"with open({str(record)!r},'w') as f:\n"
        " json.dump({'args':sys.argv,'env':dict(os.environ),'input':value},f)\n"
        "print(value,flush=True)\n"
    )
    binary.chmod(0o700)
    credential = "dummy-recovery-password-" + "x" * 48
    argocd_login.login(binary, credential)
    result = json.loads(record.read_text())
    assert result["input"] == credential
    assert credential not in json.dumps(result["args"])
    assert credential not in json.dumps(result["env"])
    assert credential not in str(capsys.readouterr())


def test_private_vault_decryption_rejects_readable_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(argocd_login, "RECOVERY", tmp_path)
    key = b"dummy-test-vault-key"
    key_file = tmp_path / "vault-password"
    key_file.write_bytes(key)
    key_file.chmod(0o600)
    password = "x" * 64
    vault = tmp_path / "argocd-admin.vault.yml"
    vault.write_bytes(
        VaultLib([("default", VaultSecret(key))]).encrypt(
            yaml.safe_dump({"argocd_admin": {"password": password}})
        )
    )
    vault.chmod(0o600)
    assert argocd_login.read_credential() == password
    vault.chmod(0o644)
    with pytest.raises(ValueError):
        argocd_login.read_credential()


def test_regeneration_and_cutoff_refresh_keep_only_encrypted_private_input(tmp_path):
    # Regeneration is break-glass after lost input; refreshing a stale cutoff
    # must retain the pending credential. Login tests do not own either behavior.
    key = b"dummy-test-vault-key"
    key_file = tmp_path / "vault-password"
    key_file.write_bytes(key)
    key_file.chmod(0o600)
    decrypt = VaultLib([("default", VaultSecret(key))]).decrypt
    target = tmp_path / "argocd-admin.vault.yml"
    argocd_admin_vault.update(tmp_path)
    first = yaml.safe_load(decrypt(target.read_bytes()))["argocd_admin"]
    assert first["password"].encode() not in target.read_bytes()
    assert target.stat().st_mode & 0o077 == 0
    assert bcrypt.checkpw(first["password"].encode(), first["password_hash"].encode())
    assert datetime.fromisoformat(first["password_mtime"]).utcoffset().total_seconds() == 0
    with pytest.raises(ValueError):
        argocd_admin_vault.update(tmp_path)
    argocd_admin_vault.update(tmp_path, refresh=True)
    second = yaml.safe_load(decrypt(target.read_bytes()))["argocd_admin"]
    assert second["password"] == first["password"]
    assert second["password_hash"] == first["password_hash"]
    assert datetime.fromisoformat(second["password_mtime"]) <= datetime.now(timezone.utc)
    argocd_admin_vault.update(tmp_path, replace=True)
    third = yaml.safe_load(decrypt(target.read_bytes()))["argocd_admin"]
    assert third["password"] != first["password"]
