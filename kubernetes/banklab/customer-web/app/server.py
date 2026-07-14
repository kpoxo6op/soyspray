#!/usr/bin/env python3
"""Serve the demo banking page and proxy its card request through Kong."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import monotonic
from uuid import uuid4

APP_DIR = Path(__file__).resolve().parent
APP_PORT = int(os.environ.get("APP_PORT", "8080"))
KONG_PROXY_URL = os.environ.get(
    "KONG_PROXY_URL",
    "http://banklab-kong-gateway-proxy.platform-kong.svc.cluster.local",
).rstrip("/")
KONG_HOST = os.environ.get("KONG_HOST", "api.internal.banklab.test")
CARDS_API_KEY = os.environ.get("CARDS_API_KEY", "")
VISIBLE_HEADERS = (
    "x-banklab-correlation-id",
    "ratelimit-limit",
    "ratelimit-remaining",
    "x-kong-proxy-latency",
    "x-kong-upstream-latency",
)
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'none'",
        "connect-src 'self'",
        "form-action 'none'",
        "frame-ancestors 'none'",
        "img-src 'self' data:",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
    )
)


def call_cards(include_key: bool) -> dict:
    request_id = f"customer-web-{uuid4()}"
    headers = {
        "Host": KONG_HOST,
        "Accept": "application/json",
        "User-Agent": "banklab-customer-web",
        "X-Request-ID": request_id,
    }
    if include_key:
        headers["apikey"] = CARDS_API_KEY

    request = urllib.request.Request(f"{KONG_PROXY_URL}/cards/v1/cards", headers=headers)
    started = monotonic()
    try:
        response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    except urllib.error.URLError as exc:
        return {"ok": False, "message": str(exc.reason), "trace": {"request_id": request_id}}

    body = response.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {"message": body.strip()}

    trace_headers = {
        name: response.headers[name]
        for name in VISIBLE_HEADERS
        if response.headers.get(name) is not None
    }
    return {
        "ok": response.status == HTTPStatus.OK,
        "expected_rejection": not include_key
        and response.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN},
        "data": data,
        "trace": {
            "status": response.status,
            "request_id": request_id,
            "elapsed_ms": round((monotonic() - started) * 1000),
            "headers": trace_headers,
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "banklab-customer-web"

    def log_message(self, fmt: str, *args: object) -> None:
        print(fmt % args, flush=True)

    def send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, status: int, payload: dict) -> None:
        self.send_bytes(status, "application/json; charset=utf-8", json.dumps(payload).encode())

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        if self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            self.send_bytes(HTTPStatus.OK, content_type, (APP_DIR / filename).read_bytes())
        elif self.path == "/ready":
            self.send_json(
                HTTPStatus.OK if CARDS_API_KEY else HTTPStatus.SERVICE_UNAVAILABLE,
                {"ready": bool(CARDS_API_KEY)},
            )
        elif self.path == "/api/cards":
            self.send_json(HTTPStatus.OK, call_cards(include_key=True))
        elif self.path == "/api/cards/without-key":
            self.send_json(HTTPStatus.OK, call_cards(include_key=False))
        elif self.path == "/favicon.ico":
            self.send_bytes(HTTPStatus.NO_CONTENT, "image/x-icon", b"")
        else:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not-found"})


if __name__ == "__main__":
    print(f"banklab customer web listening on {APP_PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", APP_PORT), Handler).serve_forever()
