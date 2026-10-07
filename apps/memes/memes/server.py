"""One-process HTTP service; access logs omit all request paths and cookies."""

import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .recommender import ALGO_VERSION
from .store import Refused, Store

STATIC = Path(__file__).with_name("static")


def server(data, address=("0.0.0.0", 8080), origin="https://memes.soyspray.vip", secure=True):
    store = Store(data)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, data, content="application/json", extra=None):
            body = json.dumps(data).encode() if content == "application/json" else data
            self.send_response(status)
            self.send_header("Content-Type", content)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def session(self):
            try:
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                return (
                    store.authenticate(cookie["memes_session"].value)
                    if "memes_session" in cookie
                    else None
                )
            except Exception:
                return None

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/healthz":
                return self.reply(
                    200,
                    {
                        "ok": True,
                        "catalog_count": len(store.catalog.items),
                        "catalog_version": store.catalog.version,
                        "algo_version": ALGO_VERSION,
                    },
                )
            if path.startswith("/t/"):
                token = path[3:]
                cookie = store.exchange(token) if 30 <= len(token) <= 100 else None
                if cookie is None:
                    return self.reply(403, {"error": "This invite is invalid."})
                flags = "; Secure" if secure else ""
                return self.reply(
                    303,
                    b"",
                    "text/plain",
                    {
                        "Location": "/",
                        "Set-Cookie": f"memes_session={cookie}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax{flags}",
                    },
                )
            session = self.session()
            if session is None:
                return self.reply(
                    401, b"Open your personal invite link to start.", "text/plain; charset=utf-8"
                )
            if path == "/api/feed":
                return self.reply(200, store.feed(session))
            if path == "/api/results":
                return self.reply(200, store.results(session))
            if path.startswith("/images/"):
                try:
                    image = store.image(session, int(path[8:]))
                except ValueError:
                    image = None
                if image is not None:
                    return self.reply(200, image.read_bytes(), "image/jpeg")
            files = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/results": ("results.html", "text/html; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript"),
                "/results.js": ("results.js", "text/javascript"),
                "/style.css": ("style.css", "text/css"),
            }
            if path in files:
                filename, content = files[path]
                return self.reply(200, (STATIC / filename).read_bytes(), content)
            self.reply(404, {"error": "Not found"})

        def do_POST(self):
            if self.headers.get("Origin") != origin:
                return self.reply(403, {"error": "Invalid origin"})
            session = self.session()
            if session is None:
                return self.reply(401, {"error": "Open your invite link."})
            path = urlsplit(self.path).path
            if path not in ("/api/render", "/api/action"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if (
                    not 0 < length <= 2048
                    or self.headers.get("Content-Type", "").split(";")[0] != "application/json"
                ):
                    raise ValueError()
                payload = json.loads(self.rfile.read(length))
                impression = payload["impression_id"]
                if type(impression) is not int or impression < 1:
                    raise ValueError()
                kind = path.rsplit("/", 1)[1]
                if kind == "action":
                    if payload["action"] not in ("like", "dislike", "skip"):
                        raise ValueError()
                    for key in ("hidden_ms", "client_seq"):
                        if type(payload[key]) is not int or not 0 <= payload[key] <= 2**31 - 1:
                            raise ValueError()
                response = store.mutate(session, impression, kind, payload)
            except Refused as error:
                return self.reply(409, {"error": str(error)})
            except (ValueError, KeyError, TypeError):
                return self.reply(400, {"error": "Invalid request"})
            self.reply(200, response)

    instance = ThreadingHTTPServer(address, Handler)
    instance.store = store
    return instance


def main():
    server(
        os.environ.get("MEMES_DATA", "/data"),
        (os.environ.get("MEMES_HOST", "0.0.0.0"), int(os.environ.get("MEMES_PORT", "8080"))),
        os.environ.get("MEMES_ORIGIN", "https://memes.soyspray.vip"),
        os.environ.get("MEMES_COOKIE_SECURE", "true") == "true",
    ).serve_forever()


if __name__ == "__main__":
    main()
