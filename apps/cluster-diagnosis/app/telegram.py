"""Deliver diagnosis messages through the Telegram Bot API directly.

The bot token lives in a mounted Secret and never in a URL that reaches a log or
an error message. Delivery is a separate step from diagnosis: a failed send is
retried from the persisted outbox without spending another model call, and a
narrative for an incident that already recovered is dropped rather than sent.
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_CHARS = 3500
REQUEST_TIMEOUT = 20.0
MAX_RESPONSE_BYTES = 32 * 1024
MAX_OUTBOX = 20
MAX_OUTBOX_AGE_SECONDS = 6 * 3600


def fit_message(message: str, limit: int = MAX_MESSAGE_CHARS) -> str:
    """Trim on a line boundary so a cut never lands mid-sentence."""
    if len(message) <= limit:
        return message
    trimmed = message[: limit - 32]
    cut = trimmed.rfind("\n")
    if cut > 0:
        trimmed = trimmed[:cut]
    return trimmed + "\n... (truncated)"


def default_transport(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "soyspray-cluster-diagnosis/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                return response.status, None
            return response.status, json.loads(body)
    except HTTPError as error:
        detail: Any = None
        try:
            detail = json.loads(error.read(MAX_RESPONSE_BYTES))
        except Exception:  # noqa: BLE001 - an error body is optional
            detail = None
        return error.code, detail


class Telegram:
    """Send plain text to one fixed chat. The recipient is never model output."""

    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        transport: Callable[[str, dict[str, Any], float], tuple[int, Any]] = default_transport,
    ):
        self.token = token
        self.chat_id = chat_id
        self.transport = transport

    def _url(self) -> str:
        return f"{TELEGRAM_API}/bot{self.token}/sendMessage"

    def send(self, message: str) -> dict[str, Any]:
        if not self.token or not self.chat_id:
            return {"status": "unavailable", "cause": "no-credentials"}
        payload = {
            "chat_id": self.chat_id,
            "text": fit_message(message),
            "disable_web_page_preview": True,
            "disable_notification": False,
        }
        try:
            status, body = self.transport(self._url(), payload, REQUEST_TIMEOUT)
        except (URLError, TimeoutError, OSError, ValueError):
            # Telegram may have accepted the message before the client gave up.
            return {"status": "unavailable", "cause": "network"}
        if status != 200 or not isinstance(body, dict) or body.get("ok") is not True:
            cause = f"http-{status}" if status and status != 200 else "rejected"
            if isinstance(body, dict):
                description = body.get("description")
                if isinstance(description, str):
                    cause = f"{cause}: {description[:80]}"
            return {"status": "unavailable", "cause": cause}
        return {"status": "sent", "cause": ""}

    def healthy(self) -> bool:
        return bool(self.token and self.chat_id)


def enqueue(outbox: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Add one pending message, bounded in count so the file cannot grow."""
    outbox.append(entry)
    return outbox[-MAX_OUTBOX:]


def expired(entry: dict[str, Any], now: float) -> bool:
    value = entry.get("queued_at")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # An entry without a queue time cannot be aged, so it is dropped rather
        # than kept forever.
        return True
    return now - float(value) > MAX_OUTBOX_AGE_SECONDS
