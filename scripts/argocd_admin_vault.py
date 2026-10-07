"""Generate the private Argo admin Vault, or refresh its rotation cutoff."""

import argparse
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

RECOVERY = Path.home() / ".config/soyspray/recovery"


def update(recovery, *, replace=False, refresh=False):
    key = recovery / "vault-password"
    target = recovery / "argocd-admin.vault.yml"
    if key.is_symlink() or key.stat().st_mode & 0o077:
        raise ValueError("The Vault key must be private.")
    vault = VaultLib([("default", VaultSecret(key.read_bytes().strip()))])
    if target.exists() and not (replace or refresh):
        raise ValueError("Vault already exists; choose replacement or cutoff refresh explicitly.")
    if refresh:
        if target.is_symlink() or target.stat().st_mode & 0o077:
            raise ValueError("The Vault must be private.")
        value = yaml.safe_load(vault.decrypt(target.read_bytes()))["argocd_admin"]
        if set(value) != {"password", "password_hash", "password_mtime"}:
            raise ValueError("The Vault has unexpected fields.")
        if not bcrypt.checkpw(value["password"].encode(), value["password_hash"].encode()):
            raise ValueError("Credential and hash disagree.")
    else:
        password = secrets.token_urlsafe(48)
        value = {
            "password": password,
            "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode(),
        }
    value["password_mtime"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ciphertext = vault.encrypt(yaml.safe_dump({"argocd_admin": value}))
    # The temporary file contains ciphertext only and has mode 0600.
    with tempfile.NamedTemporaryFile(dir=recovery, delete=False) as temporary:
        name = temporary.name
        try:
            temporary.write(ciphertext)
            temporary.flush()
            os.fsync(temporary.fileno())
            os.replace(name, target)
        finally:
            Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--replace", action="store_true", help="Generate another private credential")
    mode.add_argument(
        "--refresh-cutoff", action="store_true", help="Retain credential; use current UTC"
    )
    args = parser.parse_args()
    try:
        update(RECOVERY, replace=args.replace, refresh=args.refresh_cutoff)
    except Exception:
        raise SystemExit(
            "Private Vault update failed; inspect permissions and inputs locally."
        ) from None
    print("Private encrypted Argo recovery input saved with a fresh UTC cutoff.")


if __name__ == "__main__":
    main()
