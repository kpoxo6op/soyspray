"""Durable incident state that enforces the spending guard across restarts.

The state file is storage, not a cache. Losing it would hand back a fresh daily
allowance, so a missing, unreadable or incompatible file stops model calls until
an operator resets it deliberately. The file is written atomically and the
process holds an exclusive lock for its whole lifetime, so a rolling update or a
duplicate pod can never write it at the same time.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 3

DEFAULT_ATTEMPT_LIMIT = 3
DEFAULT_TOKEN_LIMIT = 60_000


class StateUnusable(RuntimeError):
    """The spend guard cannot be read, so no model call may start."""


def empty_state() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "source": None,
        "incidents": {},
        "closed": [],
        "budget": {},
        "quota": {},
        "metrics": {},
        "classifier_cache": {},
        "outbox": [],
        "blocked": None,
    }


def budget_for(state: dict[str, Any], day: str) -> dict[str, int]:
    entry = state.setdefault("budget", {}).setdefault(day, {"attempts": 0, "tokens": 0})
    for key in ("attempts", "tokens"):
        value = entry.get(key, 0)
        entry[key] = value if isinstance(value, int) and not isinstance(value, bool) else 0
    return entry


def reserve(
    state: dict[str, Any],
    day: str,
    *,
    tokens: int,
    attempt_limit: int = DEFAULT_ATTEMPT_LIMIT,
    token_limit: int = DEFAULT_TOKEN_LIMIT,
) -> tuple[bool, str]:
    """Reserve one transmission and its token ceiling before it is sent.

    Returns whether the reservation was made and, when it was not, why. The
    caller must save the state before opening the connection, so a request that
    completes remotely but is never observed still counts.
    """
    entry = budget_for(state, day)
    if entry["attempts"] >= attempt_limit:
        return False, "daily-attempts"
    if entry["tokens"] + tokens > token_limit:
        return False, "daily-tokens"
    entry["attempts"] += 1
    entry["tokens"] += max(0, int(tokens))
    return True, ""


def charge_tokens(
    state: dict[str, Any], day: str, *, reserved: int, used: int, known: bool = True
) -> None:
    """Replace a reservation with what the provider actually reported.

    When the answer never arrived, the reservation stands. The request may have
    been served and billed, and releasing it would hand that spend back as if it
    had never happened.
    """
    if not known:
        return
    entry = budget_for(state, day)
    entry["tokens"] = max(0, entry["tokens"] - max(0, int(reserved)) + max(0, int(used)))


class StateStore:
    """One private JSON file with an exclusive process lock."""

    def __init__(self, path: Path, lock_path: Path | None = None):
        self.path = Path(path)
        self.lock_path = Path(lock_path) if lock_path else self.path.with_suffix(".lock")
        self._lock_file: Any = None

    def acquire(self) -> bool:
        """Take the exclusive lock for this process, or report that another holds it."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = self.lock_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock_file.close()
            self._lock_file = None
            return False
        return True

    def release(self) -> None:
        if self._lock_file is None:
            return
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
        self._lock_file.close()
        self._lock_file = None

    def load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            # First start. The operator seeds or accepts a fresh budget.
            return empty_state()
        except (OSError, ValueError, UnicodeError) as error:
            raise StateUnusable(f"state file is unreadable: {type(error).__name__}") from None
        if not isinstance(value, dict) or value.get("version") != SCHEMA_VERSION:
            raise StateUnusable("state file has an unsupported schema version")
        for name, default in empty_state().items():
            value.setdefault(name, default)
        return value

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(state, stream, sort_keys=True, indent=1)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            # The rename must survive a power loss to keep the guard honest.
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def reset(self) -> dict[str, Any]:
        """Replace the state with a fresh one. The caller must hold the lock."""
        state = empty_state()
        self.save(state)
        return state


def day_key(moment: datetime) -> str:
    return moment.date().isoformat()
