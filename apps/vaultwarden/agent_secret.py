#!/usr/bin/env python3
"""Read only the explicitly approved credentials through the restricted account."""

from __future__ import annotations

import argparse
import base64
import fcntl
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ITEM_NAME = "hays-online-timesheets"
PHONE_ITEMS = ("Phone unlock PIN", "ASB app login", "BNZ app login")
ALLOWED_ITEMS = (ITEM_NAME, *PHONE_ITEMS)
VAULT_URL = "https://vault.soyspray.vip"
BOOTSTRAP_SECRET = "vaultwarden-agent-login"


class AgentSecretError(RuntimeError):
    """A safe error that contains no secret values."""


def run(command: list[str], environment: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=180,
        )
    except FileNotFoundError as error:
        raise AgentSecretError(f"required command is missing: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        action = " ".join(command[:2])
        raise AgentSecretError(f"command failed: {action}") from error
    except subprocess.TimeoutExpired as error:
        raise AgentSecretError("credential command timed out") from error
    return result.stdout.strip()


def read_bootstrap() -> tuple[str, str]:
    output = run(
        [
            "kubectl",
            "-n",
            "vaultwarden",
            "get",
            "secret",
            BOOTSTRAP_SECRET,
            "-o",
            "json",
        ]
    )
    try:
        data = json.loads(output)["data"]
        email = base64.b64decode(data["email"], validate=True).decode()
        password = base64.b64decode(data["master-password"], validate=True).decode()
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentSecretError("the Vaultwarden agent login Secret is invalid") from error
    if not email or not password:
        raise AgentSecretError("the Vaultwarden agent login Secret is empty")
    return email, password


def appdata_directory() -> Path:
    state_root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    directory = state_root / "bw-hays-agent"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    return directory


def read_item(name: str) -> dict[str, str]:
    if name not in ALLOWED_ITEMS:
        raise AgentSecretError("item is not allowed")
    if shutil.which("kubectl") is None:
        raise AgentSecretError("required command is missing: kubectl")
    if shutil.which("bw") is None:
        raise AgentSecretError("required command is missing: bw")

    directory = appdata_directory()
    lock_path = directory / ".lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        lock_path.chmod(0o600)
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        email, password = read_bootstrap()
        environment = os.environ.copy()
        environment.pop("BW_SESSION", None)
        environment["BITWARDENCLI_APPDATA_DIR"] = str(directory)
        environment["BW_PASSWORD"] = password

        try:
            status_data = json.loads(run(["bw", "status", "--nointeraction"], environment))
            status = status_data["status"]
            if status != "unauthenticated" and status_data.get("userEmail") != email:
                run(["bw", "logout", "--quiet", "--nointeraction"], environment)
                status = "unauthenticated"
            if status == "unlocked":
                run(["bw", "lock", "--quiet", "--nointeraction"], environment)
                status = "locked"
            if status == "unauthenticated":
                run(
                    ["bw", "config", "server", VAULT_URL, "--quiet", "--nointeraction"],
                    environment,
                )
                session = run(
                    [
                        "bw",
                        "login",
                        email,
                        "--passwordenv",
                        "BW_PASSWORD",
                        "--raw",
                        "--nointeraction",
                    ],
                    environment,
                )
            elif status == "locked":
                session = run(
                    [
                        "bw",
                        "unlock",
                        "--passwordenv",
                        "BW_PASSWORD",
                        "--raw",
                        "--nointeraction",
                    ],
                    environment,
                )
            else:
                raise AgentSecretError(f"unexpected Bitwarden CLI state: {status}")
            if not session:
                raise AgentSecretError("Bitwarden CLI returned an empty session")

            environment.pop("BW_PASSWORD", None)
            environment["BW_SESSION"] = session
            run(["bw", "sync", "--quiet", "--nointeraction"], environment)
            if name == ITEM_NAME:
                item = json.loads(run(["bw", "get", "item", name, "--nointeraction"], environment))
            else:
                items = json.loads(
                    run(["bw", "list", "items", "--search", name, "--nointeraction"], environment)
                )
                matches = [
                    entry
                    for entry in items
                    if entry.get("name") == name and not entry.get("deletedDate")
                ]
                if len(matches) != 1:
                    raise AgentSecretError("the requested item is missing or ambiguous")
                item = matches[0]
            if item.get("name") != name or item.get("deletedDate"):
                raise AgentSecretError("the requested item does not match")
            login = item["login"]
            username = login.get("username") or ""
            item_password = login["password"]
            if not isinstance(username, str) or (name == ITEM_NAME and not username):
                raise AgentSecretError("the Hays item has no username")
            if not isinstance(item_password, str) or not item_password:
                raise AgentSecretError("the Hays item has no password")
            result = {"username": username, "password": item_password}
            if name in PHONE_ITEMS:
                for field in ("password", "pin", "username"):
                    custom = [
                        entry.get("value")
                        for entry in item.get("fields") or []
                        if str(entry.get("name", "")).casefold() == field
                    ]
                    if len(custom) > 1:
                        raise AgentSecretError("the requested item has ambiguous fields")
                    value = (
                        custom[0]
                        if custom
                        else (item_password if field == "pin" else login.get(field) or "")
                    )
                    if not isinstance(value, str) or "\x00" in value:
                        raise AgentSecretError("the requested item has an invalid field")
                    result[field] = value
            return result
        except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
            raise AgentSecretError("the requested item is invalid") from error
        finally:
            environment.pop("BW_PASSWORD", None)
            try:
                run(["bw", "lock", "--quiet", "--nointeraction"], environment)
            except AgentSecretError:
                pass
            environment.pop("BW_SESSION", None)


def read_hays_item() -> dict[str, str]:
    """Preserve the Hays import API and its two-field output."""
    return read_item(ITEM_NAME)


def main() -> int:
    parser = argparse.ArgumentParser(prog="agent-secret")
    parser.add_argument("action", choices=["read"])
    parser.add_argument("name", choices=ALLOWED_ITEMS)
    arguments = parser.parse_args()
    try:
        print(json.dumps(read_item(arguments.name), separators=(",", ":")))
    except AgentSecretError as error:
        print(f"agent-secret: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
