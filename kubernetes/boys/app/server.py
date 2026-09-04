#!/usr/bin/env python3
"""Serve the boys availability calendar."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import ipaddress
import json
import os
import sqlite3
import ssl
import threading
import time
import unicodedata
from datetime import date, timedelta
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

APP_DIR = Path(__file__).resolve().parent
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
        "form-action 'self'",
        "frame-ancestors 'none'",
        "img-src 'self' data:",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
    )
)
SESSION_MAX_AGE = 90 * 24 * 60 * 60
FAILED_PIN_LIMIT = 10
FAILED_PIN_WINDOW = 10 * 60
FAILED_PIN_CLIENT_LIMIT = 4096
PIN_HASH_ROUNDS = 200_000
CREW = (
    "Boris K",
    "Sergey Kiktev",
    "Max Edin",
    "Innok Mikhalev",
    "Alexey Pichulev",
    "Vitaly Borisov",
    "Eugene Kobyak",
    "Konstantin Pastbin",
    "Bronislav",
)
CREW_BY_KEY = {name.casefold(): name for name in CREW}


def normalize_name(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        raise ValueError("Enter your name.")
    name = " ".join(unicodedata.normalize("NFKC", value).split())
    if not 1 <= len(name) <= 40:
        raise ValueError("Enter a name with 1 to 40 characters.")
    if any(unicodedata.category(character).startswith("C") for character in name):
        raise ValueError("The name contains an unsupported character.")
    return name, name.casefold()


def normalize_pin(value: object) -> str:
    pin = value if isinstance(value, str) else ""
    if not 4 <= len(pin) <= 8 or not pin.isascii() or not pin.isdigit():
        raise ValueError("Use 4 to 8 digits for your PIN.")
    return pin


def hash_pin(pin: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, PIN_HASH_ROUNDS)


def encode_token(payload: dict, key: bytes) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(key, raw, hashlib.sha256).digest()
    encoded_payload = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{encoded_payload}.{encoded_signature}"


def decode_token(token: str, key: bytes) -> dict | None:
    if len(token) > 1024:
        return None
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        raw = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected = hmac.new(key, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(raw)
        if (
            not isinstance(payload, dict)
            or payload.get("version") != 2
            or int(payload.get("expires", 0)) < int(time.time())
        ):
            return None
        name, name_key = normalize_name(payload.get("name"))
        if payload.get("name_key") != name_key:
            return None
        return {"name": name, "name_key": name_key}
    except (
        binascii.Error,
        UnicodeDecodeError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ):
        return None


class BoysApp:
    def __init__(
        self,
        database_path: Path,
        seed_pin: str,
        session_key: bytes,
        assets_dir: Path = APP_DIR,
        cookie_secure: bool = True,
    ) -> None:
        if not seed_pin:
            raise ValueError("BOYS_PIN is required")
        if len(session_key) < 32:
            raise ValueError("BOYS_SESSION_KEY must contain at least 32 bytes")
        self.database_path = Path(database_path)
        self.seed_pin = seed_pin
        self.session_key = session_key
        self.assets_dir = Path(assets_dir)
        self.cookie_secure = cookie_secure
        self.failed_pins: dict[str, list[float]] = {}
        self.failed_pins_lock = threading.Lock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize_database(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    name_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pin_salt BLOB,
                    pin_hash BLOB
                );
                CREATE TABLE IF NOT EXISTS availability (
                    name_key TEXT NOT NULL REFERENCES participants(name_key) ON DELETE CASCADE,
                    day TEXT NOT NULL,
                    PRIMARY KEY (name_key, day)
                );
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(participants)")}
            if "pin_salt" not in columns:
                connection.execute("ALTER TABLE participants ADD COLUMN pin_salt BLOB")
            if "pin_hash" not in columns:
                connection.execute("ALTER TABLE participants ADD COLUMN pin_hash BLOB")
            connection.executemany(
                """
                INSERT INTO participants (name_key, name) VALUES (?, ?)
                ON CONFLICT(name_key) DO UPDATE SET name = excluded.name
                """,
                ((name.casefold(), name) for name in CREW),
            )

    def ready(self) -> bool:
        try:
            with self.connect() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def client_can_try_pin(self, client: str) -> bool:
        now = time.monotonic()
        with self.failed_pins_lock:
            recent = [
                attempted
                for attempted in self.failed_pins.get(client, [])
                if now - attempted < FAILED_PIN_WINDOW
            ]
            self.failed_pins[client] = recent
            return len(recent) < FAILED_PIN_LIMIT

    def record_failed_pin(self, client: str) -> None:
        with self.failed_pins_lock:
            if client not in self.failed_pins and len(self.failed_pins) >= FAILED_PIN_CLIENT_LIMIT:
                self.failed_pins.pop(next(iter(self.failed_pins)))
            self.failed_pins.setdefault(client, []).append(time.monotonic())

    def clear_failed_pins(self, client: str) -> None:
        with self.failed_pins_lock:
            self.failed_pins.pop(client, None)

    def create_session(self, name: str, name_key: str) -> tuple[str, str]:
        token = encode_token(
            {
                "expires": int(time.time()) + SESSION_MAX_AGE,
                "name": name,
                "name_key": name_key,
                "version": 2,
            },
            self.session_key,
        )
        return name, token

    def crew_member(self, name_value: object) -> tuple[str, str] | None:
        _, name_key = normalize_name(name_value)
        name = CREW_BY_KEY.get(name_key)
        return (name, name_key) if name else None

    def crew(self) -> list[dict]:
        with self.connect() as connection:
            claimed = {
                name_key: pin_hash is not None
                for name_key, pin_hash in connection.execute(
                    "SELECT name_key, pin_hash FROM participants"
                )
            }
        return [{"name": name, "claimed": claimed.get(name.casefold(), False)} for name in CREW]

    def login(self, name_value: object, pin_value: object, client: str) -> tuple[str, str]:
        if not self.client_can_try_pin(client):
            raise PermissionError("Too many PIN attempts. Try again in 10 minutes.")
        member = self.crew_member(name_value)
        if not member:
            self.record_failed_pin(client)
            raise PermissionError("Choose your crew name.")
        name, name_key = member
        with self.connect() as connection:
            row = connection.execute(
                "SELECT pin_salt, pin_hash FROM participants WHERE name_key = ?",
                (name_key,),
            ).fetchone()
        if not row or row[0] is None or row[1] is None:
            raise PermissionError("Claim this name first.")
        pin = pin_value if isinstance(pin_value, str) else ""
        valid_pin = 4 <= len(pin) <= 8 and pin.isascii() and pin.isdigit()
        if not valid_pin or not hmac.compare_digest(hash_pin(pin, row[0]), row[1]):
            self.record_failed_pin(client)
            raise PermissionError("The PIN is not correct.")
        self.clear_failed_pins(client)
        return self.create_session(name, name_key)

    def check_claim(
        self,
        name_value: object,
        seed_pin_value: object,
        client: str,
    ) -> tuple[str, str]:
        if not self.client_can_try_pin(client):
            raise PermissionError("Too many PIN attempts. Try again in 10 minutes.")
        seed_pin = seed_pin_value if isinstance(seed_pin_value, str) else ""
        if not hmac.compare_digest(seed_pin, self.seed_pin):
            self.record_failed_pin(client)
            raise PermissionError("The crew PIN is not correct.")
        member = self.crew_member(name_value)
        if not member:
            raise PermissionError("Choose your crew name.")
        name, name_key = member
        with self.connect() as connection:
            row = connection.execute(
                "SELECT pin_hash FROM participants WHERE name_key = ?",
                (name_key,),
            ).fetchone()
        if not row or row[0] is not None:
            raise ValueError("This name is already claimed.")
        self.clear_failed_pins(client)
        return name, name_key

    def claim(
        self,
        name_value: object,
        seed_pin_value: object,
        pin_value: object,
        client: str,
    ) -> tuple[str, str]:
        name, name_key = self.check_claim(name_value, seed_pin_value, client)
        pin = normalize_pin(pin_value)
        if hmac.compare_digest(pin, self.seed_pin):
            raise ValueError("Choose a different PIN.")
        salt = os.urandom(16)
        pin_digest = hash_pin(pin, salt)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT pin_hash FROM participants WHERE name_key = ?",
                (name_key,),
            ).fetchone()
            if not row or row[0] is not None:
                raise ValueError("This name is already claimed.")
            connection.execute(
                "UPDATE participants SET pin_salt = ?, pin_hash = ? WHERE name_key = ?",
                (salt, pin_digest, name_key),
            )
        self.clear_failed_pins(client)
        return self.create_session(name, name_key)

    def session(self, cookie_header: str | None) -> dict | None:
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except (CookieError, ValueError):
            return None
        morsel = cookie.get("boys_session")
        session = decode_token(morsel.value, self.session_key) if morsel else None
        if not session:
            return None
        with self.connect() as connection:
            row = connection.execute(
                "SELECT pin_hash FROM participants WHERE name_key = ?",
                (session["name_key"],),
            ).fetchone()
        return session if row and row[0] is not None else None

    def availability(self, me: str) -> dict:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT participants.name, availability.day
                FROM participants
                LEFT JOIN availability USING (name_key)
                WHERE participants.name_key IN ({placeholders})
                ORDER BY participants.name_key, availability.day
                """.format(placeholders=", ".join("?" for _ in CREW)),
                tuple(name.casefold() for name in CREW),
            ).fetchall()
        grouped: dict[str, list[str]] = {}
        for name, day in rows:
            grouped.setdefault(name, [])
            if day:
                grouped[name].append(day)
        participants = [
            {"name": name, "dates": dates}
            for name, dates in sorted(grouped.items(), key=lambda item: item[0].casefold())
        ]
        return {"me": me, "participants": participants}

    def save_availability(self, session: dict, values: object) -> dict:
        if not isinstance(values, list) or len(values) > 366:
            raise ValueError("Send a list with no more than 366 dates.")
        today = date.today()
        last_day = today + timedelta(days=366)
        selected: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                raise ValueError("Select dates from today through the next year.")
            try:
                parsed = date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("Select dates from today through the next year.") from error
            if parsed < today or parsed > last_day or value != parsed.isoformat():
                raise ValueError("Select dates from today through the next year.")
            selected.add(value)

        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM availability WHERE name_key = ?", (session["name_key"],)
            )
            connection.executemany(
                "INSERT INTO availability (name_key, day) VALUES (?, ?)",
                ((session["name_key"], day) for day in sorted(selected)),
            )
        return self.availability(session["name"])


class Handler(BaseHTTPRequestHandler):
    server_version = "boys-calendar"

    @property
    def app(self) -> BoysApp:
        return self.server.boys_app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: object) -> None:
        print(fmt % args, flush=True)

    def send_bytes(
        self,
        status: int,
        content_type: str,
        body: bytes,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
        self.send_header("Strict-Transport-Security", "max-age=31536000")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(
        self,
        status: int,
        payload: dict,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_bytes(
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(),
            extra_headers,
        )

    def send_database_error(self, action: str, error: sqlite3.Error) -> None:
        print(f"database error during {action}: {type(error).__name__}", flush=True)
        self.send_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": "The calendar is temporarily unavailable."},
        )

    def read_json(self) -> dict:
        if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
            raise TypeError("Send JSON content.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("The request is not valid.") from error
        if not 0 < length <= 32768:
            raise ValueError("The request is not valid.")
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("The request is not valid JSON.") from error
        if not isinstance(payload, dict):
            raise ValueError("The request must be a JSON object.")
        return payload

    def current_session(self) -> dict | None:
        return self.app.session(self.headers.get("Cookie"))

    def client_key(self) -> str:
        forwarded = self.headers.get("CF-Connecting-IP", "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            return self.client_address[0]

    def session_cookie(self, token: str, max_age: int = SESSION_MAX_AGE) -> str:
        parts = [
            f"boys_session={token}",
            "Path=/",
            f"Max-Age={max_age}",
            "HttpOnly",
            "SameSite=Strict",
        ]
        if self.app.cookie_secure:
            parts.append("Secure")
        return "; ".join(parts)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in STATIC_FILES:
            filename, content_type = STATIC_FILES[path]
            self.send_bytes(
                HTTPStatus.OK, content_type, (self.app.assets_dir / filename).read_bytes()
            )
        elif path == "/favicon.ico":
            self.send_bytes(HTTPStatus.NO_CONTENT, "image/x-icon", b"")
        elif path == "/healthz":
            self.send_json(HTTPStatus.OK, {"ok": True})
        elif path == "/ready":
            ready = self.app.ready()
            self.send_json(
                HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE,
                {"ready": ready},
            )
        elif path == "/api/session":
            self.send_json(
                HTTPStatus.OK,
                {"authenticated": self.current_session() is not None},
            )
        elif path == "/api/crew":
            try:
                self.send_json(HTTPStatus.OK, {"crew": self.app.crew()})
            except sqlite3.Error as error:
                self.send_database_error("read crew", error)
        elif path == "/api/availability":
            session = self.current_session()
            if not session:
                self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Enter your name and PIN."})
                return
            try:
                self.send_json(HTTPStatus.OK, self.app.availability(session["name"]))
            except sqlite3.Error as error:
                self.send_database_error("read", error)
        else:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/session":
                name, token = self.app.login(
                    payload.get("name"), payload.get("pin"), self.client_key()
                )
                self.send_json(
                    HTTPStatus.OK,
                    {"name": name},
                    {"Set-Cookie": self.session_cookie(token)},
                )
            elif path == "/api/claim":
                name, token = self.app.claim(
                    payload.get("name"),
                    payload.get("seed_pin"),
                    payload.get("pin"),
                    self.client_key(),
                )
                self.send_json(
                    HTTPStatus.OK,
                    {"name": name},
                    {"Set-Cookie": self.session_cookie(token)},
                )
            elif path == "/api/claim/check":
                name, _ = self.app.check_claim(
                    payload.get("name"),
                    payload.get("seed_pin"),
                    self.client_key(),
                )
                self.send_json(HTTPStatus.OK, {"name": name})
            elif path == "/api/logout":
                self.send_json(
                    HTTPStatus.OK,
                    {"ok": True},
                    {"Set-Cookie": self.session_cookie("", 0)},
                )
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
        except PermissionError as error:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)})
        except TypeError as error:
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": str(error)})
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except sqlite3.Error as error:
            self.send_database_error("login", error)

    def do_PUT(self) -> None:
        path = urlsplit(self.path).path
        if path != "/api/availability":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        session = self.current_session()
        if not session:
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Enter your name and PIN."})
            return
        try:
            payload = self.read_json()
            self.send_json(
                HTTPStatus.OK,
                self.app.save_availability(session, payload.get("dates")),
            )
        except TypeError as error:
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": str(error)})
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except sqlite3.Error as error:
            self.send_database_error("save", error)


def make_server(address: tuple[str, int], app: BoysApp) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(address, Handler)
    server.daemon_threads = True
    server.boys_app = app  # type: ignore[attr-defined]
    return server


def main() -> None:
    seed_pin = os.environ.get("BOYS_PIN", "")
    session_key = os.environ.get("BOYS_SESSION_KEY", "").encode()
    app = BoysApp(
        database_path=Path(os.environ.get("BOYS_DATABASE", "/data/boys.sqlite3")),
        seed_pin=seed_pin,
        session_key=session_key,
        cookie_secure=os.environ.get("BOYS_COOKIE_SECURE", "true").lower() != "false",
    )
    http_port = int(os.environ.get("APP_PORT", "8080"))
    http_server = make_server(("0.0.0.0", http_port), app)
    cert_path = os.environ.get("TLS_CERT", "/tls/tls.crt")
    key_path = os.environ.get("TLS_KEY", "/tls/tls.key")
    if Path(cert_path).is_file() and Path(key_path).is_file():
        tls_port = int(os.environ.get("APP_TLS_PORT", "8443"))
        tls_server = make_server(("0.0.0.0", tls_port), app)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert_path, key_path)
        tls_server.socket = context.wrap_socket(tls_server.socket, server_side=True)
        threading.Thread(target=http_server.serve_forever, daemon=True).start()
        print(f"boys calendar listening on {http_port} and {tls_port}", flush=True)
        tls_server.serve_forever()
    else:
        print(f"boys calendar listening on {http_port}", flush=True)
        http_server.serve_forever()


if __name__ == "__main__":
    main()
