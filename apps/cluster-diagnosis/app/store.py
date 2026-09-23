"""Durable incident and delivery state across restarts.

An unreadable or incompatible file cannot be replaced silently: that would lose
the delivery outbox and duplicate notices. Writes are atomic and one process
holds the exclusive lock for its lifetime.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 3


class StateUnusable(RuntimeError):
    """Incident or delivery state cannot be read."""


def empty_state() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "source": None,
        "incidents": {},
        "closed": [],
        "metrics": {},
        "outbox": [],
    }


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
            # First start after the claim is created.
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
