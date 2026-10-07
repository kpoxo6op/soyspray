"""Log in with the private Vault credential over the CLI's terminal input."""

import os
import pty
import select
import subprocess
import termios
import time
from pathlib import Path

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

from scripts.argocd_cli import argocd

RECOVERY = Path.home() / ".config/soyspray/recovery"


def read_credential():
    vault = RECOVERY / "argocd-admin.vault.yml"
    key = RECOVERY / "vault-password"
    for path in (vault, key):
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError("Recovery input must be a private regular file.")
    plaintext = VaultLib([("default", VaultSecret(key.read_bytes().strip()))]).decrypt(
        vault.read_bytes()
    )
    credential = yaml.safe_load(plaintext)["argocd_admin"]["password"]
    if not isinstance(credential, str) or len(credential) < 40 or "\n" in credential:
        raise ValueError("Invalid private credential.")
    return credential


def login(binary, password):
    # Argo v2.14.5 uses terminal.ReadPassword, which requires a terminal FD.
    # Disable echo before spawning, wait for its prompt, and discard all output.
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    env = {k: v for k, v in os.environ.items() if not k.startswith("ARGOCD_")}
    process = None
    try:
        process = subprocess.Popen(
            [str(binary), "login", "argocd.soyspray.vip", "--username", "admin", "--grpc-web"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=env,
        )
        os.close(slave)
        slave = None
        deadline = time.monotonic() + 60
        pending = b""
        supplied = False
        while time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    pending = (pending + os.read(master, 4096))[-4096:]
                except OSError:
                    break
                if not supplied and b"Password: " in pending:
                    os.write(master, password.encode() + b"\n")
                    supplied = True
                    pending = b""
            if process.poll() is not None:
                break
        if process.poll() is None:
            process.kill()
        result = process.wait(timeout=5)
        if result != 0 or not supplied:
            raise RuntimeError("Argo login failed; check the private input and server route.")
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        if slave is not None:
            os.close(slave)


def main():
    try:
        login(argocd(), read_credential())
    except Exception:
        # Parser, Vault and CLI errors can include private data. Never echo them.
        raise SystemExit(
            "Argo login failed; check private recovery inputs and connectivity."
        ) from None
    print("Argo CD admin login succeeded.")


if __name__ == "__main__":
    main()
