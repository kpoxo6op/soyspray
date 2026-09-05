"""Validated trip documents with optimistic writes and an append-only audit."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SECTIONS = ("destination", "dates", "budget", "accommodation", "call")
ANSWERS = {"yes", "maybe", "no"}


class Conflict(ValueError):
    pass


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError("Проверьте поля документа.")
    return value


def text(value, limit=200, *, empty=True):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        raise ValueError("Проверьте текст и его длину.")
    return value.strip()


def identifier(value):
    value = text(value, 64, empty=False)
    if not value.isascii() or not all(char.isalnum() or char in "-_" for char in value):
        raise ValueError("Неверный идентификатор.")
    return value


def number(value, maximum, *, minimum=0):
    if value is None:
        return None
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Проверьте число. Неизвестное значение можно оставить пустым.")
    return value


def day(value, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise ValueError("Укажите дату в формате ГГГГ-ММ-ДД.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Проверьте дату.") from error
    if value != parsed.isoformat():
        raise ValueError("Укажите дату в формате ГГГГ-ММ-ДД.")
    return value


def stay(value, *, optional=False):
    arrival = day(value["arrival"], optional=optional)
    departure = day(value["departure"], optional=optional)
    if arrival and departure and arrival >= departure:
        raise ValueError("Дата отъезда должна быть позже даты приезда.")
    return {"arrival": arrival, "departure": departure}


def link(value):
    value = text(value, 2048)
    if value:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Укажите обычную ссылку http или https без пароля.")
    return value


def money_range(value):
    fields(value, ("min_cents", "max_cents"))
    lower = number(value["min_cents"], 100_000_000)
    upper = number(value["max_cents"], 100_000_000)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Минимальный бюджет не должен превышать максимальный.")
    return {"min_cents": lower, "max_cents": upper}


def unique_items(values, limit, validate):
    if not isinstance(values, list) or len(values) > limit:
        raise ValueError("Слишком много вариантов.")
    result = [validate(value) for value in values]
    if len({item["id"] for item in result}) != len(result):
        raise ValueError("У каждого варианта должен быть свой идентификатор.")
    return result


def option(value):
    fields(value, ("id", "label", "arrival", "departure"))
    return {
        "id": identifier(value["id"]),
        "label": text(value["label"], empty=False),
        **stay(value),
    }


def candidate(value):
    fields(
        value,
        (
            "id",
            "url",
            "title",
            "arrival",
            "departure",
            "total_cents",
            "quoted_on",
            "capacity",
            "notes",
        ),
    )
    return {
        "id": identifier(value["id"]),
        "url": link(value["url"]),
        "title": text(value["title"], empty=False),
        **stay(value, optional=True),
        "total_cents": number(value["total_cents"], 100_000_000),
        "quoted_on": day(value["quoted_on"], optional=True),
        "capacity": number(value["capacity"], 100, minimum=1),
        "notes": text(value["notes"], 1000),
    }


def selected(value, items):
    if value is not None and (
        not isinstance(value, str) or value not in {item["id"] for item in items}
    ):
        raise ValueError("Выберите существующий вариант.")
    return value


def call(value):
    fields(value, ("at", "timezone", "url"))
    if value["at"] is None:
        if value["timezone"] is not None or value["url"]:
            raise ValueError("Сначала укажите время звонка.")
        return {"at": None, "timezone": None, "url": ""}
    try:
        instant = datetime.fromisoformat(text(value["at"], 40).replace("Z", "+00:00"))
        zone = text(value["timezone"], 80, empty=False)
        if instant.tzinfo is None or not ("/" in zone or zone == "UTC"):
            raise ValueError("Укажите часовой пояс IANA и точное время.")
        ZoneInfo(zone)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("Проверьте время и часовой пояс IANA.") from error
    return {
        "at": instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "timezone": zone,
        "url": link(value["url"]),
    }


def board(value):
    fields(value, SECTIONS)
    fields(value["destination"], ("name",))
    fields(value["dates"], ("options", "selected"))
    options = unique_items(value["dates"]["options"], 12, option)
    fields(value["accommodation"], ("candidates", "selected", "paying_people"))
    candidates = unique_items(value["accommodation"]["candidates"], 12, candidate)
    return {
        "destination": {"name": text(value["destination"]["name"])},
        "dates": {"options": options, "selected": selected(value["dates"]["selected"], options)},
        "budget": money_range(value["budget"]),
        "accommodation": {
            "candidates": candidates,
            "selected": selected(value["accommodation"]["selected"], candidates),
            "paying_people": number(value["accommodation"]["paying_people"], 100, minimum=1),
        },
        "call": call(value["call"]),
    }


def response(value, options):
    fields(
        value,
        ("answers", "attendance", "arrival", "departure", "adults", "children", "notes", "budget"),
    )
    answers = value["answers"]
    if not isinstance(answers, dict) or any(
        key not in options or not isinstance(answer, str) or answer not in ANSWERS
        for key, answer in answers.items()
    ):
        raise ValueError("Проверьте ответы на варианты дат.")
    if value["attendance"] is not None and (
        not isinstance(value["attendance"], str) or value["attendance"] not in ANSWERS
    ):
        raise ValueError("Выберите да, возможно или нет.")
    return {
        "answers": answers,
        "attendance": value["attendance"],
        **stay(value, optional=True),
        "adults": number(value["adults"], 20),
        "children": number(value["children"], 20),
        "notes": text(value["notes"], 600),
        "budget": money_range(value["budget"]),
    }


def option_ranges(document):
    return {
        item["id"]: {"arrival": item["arrival"], "departure": item["departure"]}
        for item in document["dates"]["options"]
    }


def response_view(member, document, revision, options):
    visible = dict(document)
    ranges = visible.pop("answer_ranges", {})
    visible["answers"] = {
        key: answer
        for key, answer in document["answers"].items()
        if key in options and ranges.get(key) == options[key]
    }
    return {
        "name_key": member,
        "document": visible,
        "revision": revision,
        "unanswered_causes": {
            key: "dates_changed"
            for key in document["answers"]
            if key in options and ranges.get(key) != options[key]
        },
    }


def encode(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def expected(actual, revision):
    if type(revision) is not int or revision != actual:
        raise Conflict("Данные изменились. Ваш черновик сохранён в этом окне. Сравните изменения.")


class TripStore:
    def __init__(self, database, connect, members):
        self.database = Path(database)
        self.connect = connect
        self.members = set(members)
        self.initialize()

    def initialize(self):
        with self.connect() as connection:
            existing = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_schema WHERE type='table'")
            }
            tables = {"trip_documents", "trip_responses", "trip_audit"}
            if tables <= existing:
                return
            if tables & existing:
                raise ValueError("Неполная миграция поездки. Нужна проверка базы.")
            backup = self.database.with_name(
                f"{self.database.stem}.before-trip-{time.time_ns()}.sqlite3"
            )
            descriptor = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            with sqlite3.connect(backup) as target:
                connection.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise ValueError("Проверка резервной копии не пройдена.")
            with backup.open("rb") as stream:
                os.fsync(stream.fileno())
            connection.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE trip_documents (
                    id TEXT PRIMARY KEY, document TEXT NOT NULL CHECK(json_valid(document)),
                    revision INTEGER NOT NULL CHECK(revision > 0), created_at TEXT NOT NULL
                );
                CREATE TABLE trip_responses (
                    trip_id TEXT NOT NULL REFERENCES trip_documents(id),
                    name_key TEXT NOT NULL REFERENCES participants(name_key),
                    document TEXT NOT NULL CHECK(json_valid(document)),
                    revision INTEGER NOT NULL CHECK(revision > 0),
                    PRIMARY KEY(trip_id, name_key)
                );
                CREATE TABLE trip_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT NOT NULL REFERENCES trip_documents(id),
                    name_key TEXT REFERENCES participants(name_key),
                    created_at TEXT NOT NULL, action TEXT NOT NULL,
                    revision INTEGER NOT NULL, detail TEXT NOT NULL CHECK(json_valid(detail))
                );
                CREATE TRIGGER trip_audit_no_update BEFORE UPDATE ON trip_audit
                    BEGIN SELECT RAISE(ABORT, 'trip audit is append only'); END;
                CREATE TRIGGER trip_audit_no_delete BEFORE DELETE ON trip_audit
                    BEGIN SELECT RAISE(ABORT, 'trip audit is append only'); END;
                COMMIT;
            """)

    def actor(self, connection, member):
        row = connection.execute(
            "SELECT pin_hash FROM participants WHERE name_key = ?", (member,)
        ).fetchone()
        if member not in self.members or not row or row[0] is None:
            raise PermissionError("Войдите под своим именем.")

    def audit(self, connection, trip, actor, action, revision, detail):
        connection.execute(
            "INSERT INTO trip_audit(trip_id,name_key,created_at,action,revision,detail) VALUES(?,?,?,?,?,?)",
            (trip, actor, now(), action, revision, encode(detail)),
        )

    def seed(self, path):
        data = Path(path).read_bytes()
        if len(data) > 65536:
            raise ValueError("Слишком большой файл начальной поездки.")
        value = json.loads(data)
        fields(value, ("id", "document"))
        trip = identifier(value["id"])
        document = board(value["document"])
        document["decisions"] = {
            section: {"status": "draft", "by": None, "at": None} for section in SECTIONS
        }
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT id FROM trip_documents").fetchall()
            if existing:
                if existing != [(trip,)]:
                    raise ValueError(
                        "Начальная поездка отличается от существующей. Данные не изменены."
                    )
                return
            connection.execute(
                "INSERT INTO trip_documents VALUES(?,?,1,?)", (trip, encode(document), now())
            )
            self.audit(connection, trip, None, "seed", 1, {})

    def current(self, connection):
        row = connection.execute(
            "SELECT id,document,revision FROM trip_documents ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            raise LookupError("Поездка ещё не настроена.")
        return {"id": row[0], "document": json.loads(row[1]), "revision": row[2]}

    def read(self, member):
        with self.connect() as connection:
            connection.execute("BEGIN")
            self.actor(connection, member)
            try:
                trip = self.current(connection)
            except LookupError:
                return {"me": member, "trip": None, "responses": []}
            responses = [
                response_view(name, json.loads(document), revision, option_ranges(trip["document"]))
                for name, document, revision in connection.execute(
                    "SELECT name_key,document,revision FROM trip_responses WHERE trip_id=? ORDER BY name_key",
                    (trip["id"],),
                )
            ]
            return {"me": member, "trip": trip, "responses": responses}

    def update(self, member, revision, value):
        values = board(value)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self.actor(connection, member)
            trip = self.current(connection)
            expected(trip["revision"], revision)
            document = trip["document"]
            changed = {
                section: {"before": document[section], "after": values[section]}
                for section in SECTIONS
                if document[section] != values[section]
            }
            if not changed:
                return trip
            for section in changed:
                document[section] = values[section]
                document["decisions"][section] = {"status": "draft", "by": None, "at": None}
            return self.write(connection, trip, member, "edit", changed)

    def write(self, connection, trip, member, action, detail):
        trip["revision"] += 1
        connection.execute(
            "UPDATE trip_documents SET document=?,revision=? WHERE id=?",
            (encode(trip["document"]), trip["revision"], trip["id"]),
        )
        self.audit(connection, trip["id"], member, action, trip["revision"], detail)
        return trip

    def decide(self, member, revision, section, agreed):
        if not isinstance(section, str) or section not in SECTIONS or type(agreed) is not bool:
            raise ValueError("Проверьте раздел и действие.")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self.actor(connection, member)
            trip = self.current(connection)
            expected(trip["revision"], revision)
            decision = trip["document"]["decisions"][section]
            status = "agreed" if agreed else "draft"
            if decision["status"] == status:
                return trip
            trip["document"]["decisions"][section] = {"status": status, "by": member, "at": now()}
            return self.write(
                connection, trip, member, "agree" if agreed else "reopen", {"section": section}
            )

    def respond(self, member, revision, value, trip_revision):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self.actor(connection, member)
            trip = self.current(connection)
            expected(trip["revision"], trip_revision)
            options = option_ranges(trip["document"])
            values = response(value, options)
            # Bind answers to the dates that the member reviewed.
            values["answer_ranges"] = {key: options[key] for key in values["answers"]}
            row = connection.execute(
                "SELECT document,revision FROM trip_responses WHERE trip_id=? AND name_key=?",
                (trip["id"], member),
            ).fetchone()
            actual = row[1] if row else 0
            expected(actual, revision)
            if row and json.loads(row[0]) == values:
                return response_view(member, values, actual, options)
            result = {"name_key": member, "document": values, "revision": actual + 1}
            connection.execute(
                "INSERT INTO trip_responses VALUES(?,?,?,?) ON CONFLICT(trip_id,name_key) DO UPDATE SET document=excluded.document,revision=excluded.revision",
                (trip["id"], member, encode(values), result["revision"]),
            )
            self.audit(
                connection,
                trip["id"],
                member,
                "response",
                result["revision"],
                {"before": json.loads(row[0]) if row else None, "after": values},
            )
            return response_view(member, values, result["revision"], options)

    def activity(self, member, before=None):
        if before is not None and (type(before) is not int or before < 1):
            raise ValueError("Проверьте номер записи.")
        with self.connect() as connection:
            self.actor(connection, member)
            trip = self.current(connection)
            rows = connection.execute(
                "SELECT id,name_key,created_at,action,revision,detail FROM trip_audit WHERE trip_id=? AND (? IS NULL OR id < ?) ORDER BY id DESC LIMIT 100",
                (trip["id"], before, before),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "by": row[1],
                    "at": row[2],
                    "action": row[3],
                    "revision": row[4],
                    "detail": json.loads(row[5]),
                }
                for row in rows
            ]
