"""Trip behavior checks with synthetic content and disposable databases."""

import copy
import importlib.util
import json
import sqlite3
import sys
import threading
import time
from http.client import HTTPConnection
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
spec = importlib.util.spec_from_file_location("trip_runtime", APP / "server.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
sys.path.remove(str(APP))


def draft():
    return {
        "destination": {"name": "Test coast"},
        "dates": {
            "options": [
                {"id": "a", "label": "Option A", "arrival": "2031-04-10", "departure": "2031-04-13"}
            ],
            "selected": None,
        },
        "budget": {"min_cents": None, "max_cents": None},
        "accommodation": {"candidates": [], "selected": None, "paying_people": None},
        "call": {"at": None, "timezone": None, "url": ""},
    }


def member_response():
    return {
        "answers": {},
        "attendance": None,
        "arrival": None,
        "departure": None,
        "adults": None,
        "children": None,
        "notes": "",
        "budget": {"min_cents": None, "max_cents": None},
    }


@pytest.fixture
def app(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"id": "test-trip", "document": draft()}))
    value = runtime.BoysApp(
        tmp_path / "boys.sqlite3",
        "1357",
        b"synthetic-trip-session-key-with-no-live-access",
        trip_seed=seed,
    )
    value.claim("Boris K", "1357", "2468", "first")
    value.claim("Sergey Kiktev", "1357", "5678", "second")
    return value


def test_seed_is_draft_unanswered_and_never_resets_edits(app, tmp_path):
    first = app.trips.read("boris k")
    assert first["responses"] == []
    assert first["trip"]["revision"] == 1
    assert all(
        item == {"status": "draft", "by": None, "at": None}
        for item in first["trip"]["document"]["decisions"].values()
    )
    updated = draft()
    updated["destination"]["name"] = "Another test coast"
    app.trips.update("boris k", 1, updated)
    app.trips.seed(tmp_path / "seed.json")
    assert app.trips.read("boris k")["trip"]["document"]["destination"] == updated["destination"]
    assert [event["action"] for event in app.trips.activity("boris k")] == ["edit", "seed"]
    assert len(list(tmp_path.glob("*.before-trip-*.sqlite3"))) == 1
    runtime.BoysApp(app.database_path, "1357", app.session_key, trip_seed=tmp_path / "seed.json")
    assert len(list(tmp_path.glob("*.before-trip-*.sqlite3"))) == 1


def test_agreements_are_attributed_and_edits_reopen_only_changed_sections(app):
    agreed = app.trips.decide("boris k", 1, "destination", True)
    decision = agreed["document"]["decisions"]["destination"]
    assert (
        decision["status"] == "agreed"
        and decision["by"] == "boris k"
        and decision["at"].endswith("Z")
    )
    reopened = app.trips.decide("sergey kiktev", 2, "destination", False)
    assert reopened["document"]["decisions"]["destination"]["by"] == "sergey kiktev"
    app.trips.decide("sergey kiktev", 3, "destination", True)
    updated = draft()
    updated["budget"]["max_cents"] = 12345
    result = app.trips.update("boris k", 4, updated)
    assert result["document"]["decisions"]["destination"]["status"] == "agreed"
    updated["destination"]["name"] = "Changed coast"
    result = app.trips.update("boris k", 5, updated)
    assert result["document"]["decisions"]["destination"] == {
        "status": "draft",
        "by": None,
        "at": None,
    }
    log = app.trips.activity("boris k")
    assert [row["by"] for row in log[:4]] == [
        "boris k",
        "boris k",
        "sergey kiktev",
        "sergey kiktev",
    ]
    assert app.trips.activity("boris k", before=log[1]["id"])[0]["id"] == log[2]["id"]


def test_responses_are_own_data_and_old_answers_do_not_follow_changed_dates(app):
    response = member_response()
    response["answers"] = {"a": "yes"}
    response["budget"] = {"min_cents": 0, "max_cents": 12345}
    saved = app.trips.respond("boris k", 0, response, 1)
    assert saved["document"] == response
    assert app.trips.read("sergey kiktev")["responses"] == [saved]
    other = member_response()
    other["attendance"] = "maybe"
    app.trips.respond("sergey kiktev", 0, other, 1)
    with pytest.raises(runtime.Conflict):
        app.trips.respond("boris k", 0, other, 1)
    changed = draft()
    changed["dates"]["options"][0]["departure"] = "2031-04-14"
    app.trips.update("sergey kiktev", 1, changed)
    answers = {row["name_key"]: row for row in app.trips.read("boris k")["responses"]}
    assert answers["boris k"]["document"]["answers"] == {}
    assert answers["boris k"]["unanswered_causes"] == {"a": "dates_changed"}
    assert answers["boris k"]["revision"] == 1
    assert answers["sergey kiktev"]["document"] == other
    with pytest.raises(runtime.Conflict):
        app.trips.respond("boris k", 1, response, 1)
    app.trips.respond("boris k", 1, response, 2)
    assert app.trips.read("boris k")["responses"][0]["document"]["answers"] == {"a": "yes"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("attendance", "unknown"),
        ("attendance", []),
        ("answers", {"a": []}),
        ("answers", {"missing": "yes"}),
        ("adults", True),
        ("children", -1),
        ("notes", "x" * 601),
        ("budget", {"min_cents": 1.2, "max_cents": None}),
        ("budget", {"min_cents": 2, "max_cents": 1}),
    ],
)
def test_response_validation_has_no_partial_write(app, field, value):
    response = member_response()
    response[field] = value
    before = app.trips.activity("boris k")
    with pytest.raises(ValueError):
        app.trips.respond("boris k", 0, response, 1)
    assert app.trips.read("boris k")["responses"] == []
    assert app.trips.activity("boris k") == before


def test_call_stores_utc_and_iana_zone_and_money_stays_integer(app):
    value = draft()
    value["call"] = {
        "at": "2031-01-12T19:30:00+13:00",
        "timezone": "Pacific/Auckland",
        "url": "https://example.com/call",
    }
    value["budget"] = {"min_cents": 0, "max_cents": 12345}
    saved = app.trips.update("boris k", 1, value)
    assert saved["document"]["call"] == {
        "at": "2031-01-12T06:30:00Z",
        "timezone": "Pacific/Auckland",
        "url": "https://example.com/call",
    }
    assert saved["document"]["budget"] == value["budget"]
    for call in (
        {"at": "2031-01-12T19:30", "timezone": "Pacific/Auckland", "url": ""},
        {"at": "2031-01-12T19:30Z", "timezone": "Made/Up", "url": ""},
        {"at": "2031-01-12T19:30Z", "timezone": "Pacific/Auckland", "url": "javascript:alert(1)"},
    ):
        invalid = copy.deepcopy(value)
        invalid["call"] = call
        with pytest.raises(ValueError):
            app.trips.update("boris k", 2, invalid)
    assert app.trips.read("boris k")["trip"] == saved


def test_conflicts_and_audit_failures_leave_the_board_unchanged(app):
    before = app.trips.read("boris k")
    changed = draft()
    changed["destination"]["name"] = "Changed coast"
    for revision in (0, True, "1", None):
        with pytest.raises(runtime.Conflict):
            app.trips.update("boris k", revision, changed)
    with app.connect() as connection:
        connection.execute(
            "CREATE TRIGGER fail_trip_audit BEFORE INSERT ON trip_audit BEGIN SELECT RAISE(ABORT, 'test'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        app.trips.update("boris k", 1, changed)
    assert app.trips.read("boris k") == before
    with app.connect() as connection:
        for statement in ("UPDATE trip_audit SET action='changed'", "DELETE FROM trip_audit"):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)


def test_concurrent_board_updates_have_one_winner(app):
    barrier = threading.Barrier(2)
    results = []

    def update(member):
        value = draft()
        value["destination"]["name"] = member
        barrier.wait(timeout=3)
        try:
            results.append(app.trips.update(member, 1, value))
        except runtime.Conflict:
            results.append("conflict")

    threads = [
        threading.Thread(target=update, args=(member,)) for member in ("boris k", "sergey kiktev")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert results.count("conflict") == 1
    assert app.trips.read("boris k")["trip"] == next(
        value for value in results if value != "conflict"
    )
    assert len(app.trips.activity("boris k")) == 2


def request(server, method, path, payload=None, cookie=None):
    connection = HTTPConnection(*server.server_address, timeout=3)
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    connection.request(method, path, json.dumps(payload) if payload is not None else None, headers)
    response = connection.getresponse()
    body = response.read()
    status = response.status
    connection.close()
    return status, json.loads(body)


def test_http_requires_authentication_and_cannot_set_another_members_response(app):
    server = runtime.make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for method, path in (
            ("GET", "/api/trip"),
            ("GET", "/api/trip/activity"),
            ("PUT", "/api/trip"),
            ("PUT", "/api/trip/response"),
            ("POST", "/api/trip/decision"),
        ):
            status, body = request(server, method, path, {})
            assert status == 401 and "Test coast" not in json.dumps(body)
        _, token = app.login("Boris K", "2468", "http")
        cookie = "boys_session=" + token
        status, body = request(server, "GET", "/api/trip", cookie=cookie)
        assert status == 200 and body["me"] == "boris k"
        response = {
            "document": member_response(),
            "expected_revision": 0,
            "expected_trip_revision": 1,
        }
        assert (
            request(
                server,
                "PUT",
                "/api/trip/response",
                {**response, "name_key": "sergey kiktev"},
                cookie,
            )[0]
            == 400
        )
        assert (
            request(server, "PUT", "/api/trip/responses/sergey%20kiktev", response, cookie)[0]
            == 404
        )
        assert app.trips.read("boris k")["responses"] == []
        assert request(server, "PUT", "/api/trip/response", response, cookie)[0] == 200
        assert request(server, "PUT", "/api/trip/response", response, cookie)[0] == 409
        assert app.trips.read("boris k")["responses"][0]["name_key"] == "boris k"
        with pytest.raises(PermissionError):
            app.trips.read("max edin")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_additive_migration_backs_up_and_preserves_legacy_data_and_session(tmp_path):
    database = tmp_path / "boys.sqlite3"
    salt = b"synthetic-salt-16"
    pin_hash = runtime.hash_pin("2468", salt)
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE participants(name_key TEXT PRIMARY KEY,name TEXT NOT NULL,pin_salt BLOB,pin_hash BLOB);
            CREATE TABLE availability(name_key TEXT NOT NULL REFERENCES participants(name_key),day TEXT NOT NULL,PRIMARY KEY(name_key,day));
            CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL DEFAULT '2030-01-01T00:00:00Z',name_key TEXT NOT NULL REFERENCES participants(name_key),action TEXT NOT NULL,available_days INTEGER);
        """)
        connection.execute(
            "INSERT INTO participants VALUES('boris k','Boris K',?,?)", (salt, pin_hash)
        )
        connection.execute("INSERT INTO availability VALUES('boris k','2020-01-02')")
        connection.execute(
            "INSERT INTO events(name_key,action,available_days) VALUES('boris k','availability',1)"
        )
    key = b"synthetic-migration-key-with-no-live-access"
    token = runtime.encode_token(
        {
            "name": "Boris K",
            "name_key": "boris k",
            "version": 2,
            "expires": int(time.time()) + 3600,
        },
        key,
    )
    app = runtime.BoysApp(database, "1357", key)
    backups = list(tmp_path.glob("*.before-trip-*.sqlite3"))
    assert len(backups) == 1 and backups[0].stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(backups[0]) as before, app.connect() as after:
        assert before.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        old_tables = {
            row[0] for row in before.execute("SELECT name FROM sqlite_schema WHERE type='table'")
        }
        new_tables = {
            row[0] for row in after.execute("SELECT name FROM sqlite_schema WHERE type='table'")
        }
        assert new_tables - old_tables == {"trip_documents", "trip_responses", "trip_audit"}
        for table in ("participants", "availability", "events"):
            assert (
                before.execute(f"SELECT * FROM {table}").fetchall()
                == after.execute(f"SELECT * FROM {table}").fetchall()
            )
            assert (
                before.execute("SELECT sql FROM sqlite_schema WHERE name=?", (table,)).fetchone()
                == after.execute("SELECT sql FROM sqlite_schema WHERE name=?", (table,)).fetchone()
            )
        assert after.execute("PRAGMA foreign_key_check").fetchall() == []
    assert app.session("boys_session=" + token)["name_key"] == "boris k"
    assert app.login("Boris K", "2468", "preserved")[0] == "Boris K"
    # Opening a restored backup runs the same additive migration without resetting old data.
    restored = tmp_path / "restored.sqlite3"
    with sqlite3.connect(backups[0]) as source, sqlite3.connect(restored) as target:
        source.backup(target)
    recovered = runtime.BoysApp(restored, "1357", key)
    assert recovered.availability("Boris K") == app.availability("Boris K")
    assert recovered.events() == app.events()
    assert recovered.session("boys_session=" + token)["name_key"] == "boris k"


def test_accommodation_accepts_unknowns_and_validates_quotes_without_fetching(app):
    value = draft()
    candidate = {
        "id": "stay-a",
        "title": "Example stay",
        "url": "https://example.com/stay",
        "arrival": "2031-04-10",
        "departure": "2031-04-13",
        "total_cents": 123456,
        "quoted_on": "2030-12-01",
        "capacity": 9,
        "notes": "Synthetic quote",
    }
    value["accommodation"] = {
        "candidates": [candidate],
        "selected": "stay-a",
        "paying_people": None,
    }
    saved = app.trips.update("boris k", 1, value)
    assert saved["document"]["accommodation"] == value["accommodation"]
    for key, invalid in (
        ("total_cents", 1.5),
        ("total_cents", -1),
        ("capacity", False),
        ("url", "https://user:password@example.com"),
        ("departure", "2031-04-09"),
    ):
        changed = copy.deepcopy(value)
        changed["accommodation"]["candidates"][0][key] = invalid
        with pytest.raises(ValueError):
            app.trips.update("boris k", 2, changed)
    assert app.trips.read("boris k")["trip"] == saved
