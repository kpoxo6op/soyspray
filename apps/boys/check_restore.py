"""Check restored Boys data on a disposable copy. Never write to the supplied database."""

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import time
from http.client import HTTPConnection
from pathlib import Path


def database_state(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("BEGIN")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise CheckFailure("SQLite integrity check failed.")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise CheckFailure("SQLite foreign-key check failed.")
        tables = {}
        for name, schema in connection.execute(
            "SELECT name,sql FROM sqlite_schema WHERE type='table'"
        ).fetchall():
            quoted = '"' + name.replace('"', '""') + '"'
            rows = connection.execute("SELECT * FROM " + quoted).fetchall()
            values = sorted(
                json.dumps(row, sort_keys=True, default=lambda b: {"bytes": b.hex()})
                for row in rows
            )
            tables[name] = {
                "rows": len(rows),
                "hash": hashlib.sha256((schema + "\n" + "\n".join(values)).encode()).hexdigest(),
            }
        return tables


class CheckFailure(ValueError):
    pass


def require(value, cause):
    if not value:
        raise CheckFailure(cause)


def check(database, runtime, inputs):
    before = database_state(database)
    require(
        {"participants", "availability", "events"} <= before.keys(),
        "The restored file is not a Boys database.",
    )
    sys.path.insert(0, str(runtime))
    spec = importlib.util.spec_from_file_location("boys_restored", runtime / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pin, key = inputs["boys_pin"], inputs["boys_session_key"].encode()
    require(isinstance(pin, str) and len(key) >= 32, "The restored runtime inputs are invalid.")
    require(before["participants"]["rows"] == len(module.CREW), "The restored crew is incomplete.")
    with tempfile.TemporaryDirectory(prefix="boys-data-check-") as directory:
        copy = Path(directory) / "checked.sqlite3"
        with (
            sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as source,
            sqlite3.connect(copy) as target,
        ):
            source.backup(target)
        copy.chmod(0o600)
        with sqlite3.connect(copy) as connection:
            participants = connection.execute(
                "SELECT name_key,name,pin_salt,pin_hash FROM participants ORDER BY name_key"
            ).fetchall()
            dates = connection.execute(
                "SELECT name_key,day FROM availability ORDER BY name_key,day"
            ).fetchall()
            events = connection.execute("SELECT * FROM events ORDER BY id").fetchall()
        claimed = next((row for row in participants if row[3] is not None), None)
        unclaimed = next((row for row in participants if row[3] is None), None)
        token = (
            module.encode_token(
                {
                    "version": 2,
                    "name": claimed[1],
                    "name_key": claimed[0],
                    "expires": int(time.time()) + 3600,
                },
                key,
            )
            if claimed
            else None
        )
        app = module.BoysApp(copy, pin, key, assets_dir=runtime)
        initialized = database_state(copy)
        require(
            all(initialized.get(name) == value for name, value in before.items()),
            "Starting the restored app changed existing records.",
        )
        module.Handler.log_message = lambda *args: None
        server = module.make_server(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def request(method, path, data=None, cookie=None):
            headers = {"Content-Type": "application/json"}
            if cookie:
                headers["Cookie"] = cookie
            connection = HTTPConnection(*server.server_address, timeout=10)
            try:
                connection.request(
                    method, path, json.dumps(data) if data is not None else None, headers
                )
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        result = {
            "data_checks": "passed",
            "sqlite_integrity": "passed",
            "authenticated_data_read": {
                "value": "unknown",
                "cause": "The backup has no claimed member.",
            },
            "records_preserved_at_startup": "passed",
            "rows": {name: value["rows"] for name, value in before.items()},
            "legacy_session_format": {
                "value": "unknown",
                "cause": "The backup has no claimed member.",
            },
            "claim_race": {"value": "unknown", "cause": "The backup has no unclaimed member."},
            "human_personal_pin": {
                "value": "unknown",
                "cause": "No human personal PIN was supplied or guessed.",
            },
            "existing_browser_cookie": {
                "value": "unknown",
                "cause": "This check uses a legacy-format test token, not a saved browser cookie.",
            },
        }
        try:
            require(
                request("GET", "/ready") == (200, {"ready": True}), "The restored app is not ready."
            )
            for path in ("/api/availability", "/api/events", "/api/trip", "/api/trip/activity"):
                require(
                    request("GET", path)[0] == 401,
                    "Private restored data was exposed without authentication.",
                )
            if claimed:
                cookie = "boys_session=" + token
                require(
                    request("GET", "/api/session", cookie=cookie) == (200, {"authenticated": True}),
                    "Legacy session format was rejected.",
                )
                availability = request("GET", "/api/availability", cookie=cookie)
                require(availability[0] == 200, "Restored availability could not be read.")
                actual = sorted(
                    (member["name"].casefold(), day)
                    for member in availability[1]["participants"]
                    for day in member["dates"]
                )
                require(actual == dates, "The restored calendar did not return every saved date.")
                require(
                    len(request("GET", "/api/events", cookie=cookie)[1]["events"]) == len(events),
                    "The restored history did not return every event.",
                )
                trip = request("GET", "/api/trip", cookie=cookie)
                require(trip[0] == 200, "The restored trip could not be read.")
                with sqlite3.connect(copy) as connection:
                    stored = connection.execute(
                        "SELECT id,document,revision FROM trip_documents ORDER BY created_at DESC LIMIT 1"
                    ).fetchone()
                expected = (
                    {"id": stored[0], "document": json.loads(stored[1]), "revision": stored[2]}
                    if stored
                    else None
                )
                require(
                    trip[1]["trip"] == expected,
                    "The restored trip differs from its saved document.",
                )
                require(
                    request("GET", "/api/trip/activity", cookie=cookie)[0] == 200,
                    "Restored trip activity could not be read.",
                )
                require(
                    request(
                        "POST", "/api/claim", {"name": claimed[1], "seed_pin": pin, "pin": "672345"}
                    )[0]
                    == 400,
                    "The crew PIN could reset a claimed name.",
                )
                result["legacy_session_format"] = {"value": "passed"}
                result["authenticated_data_read"] = {"value": "passed"}
            if unclaimed:
                barrier = threading.Barrier(2)

                def compete(personal_pin):
                    barrier.wait(timeout=10)
                    return personal_pin, request(
                        "POST",
                        "/api/claim",
                        {"name": unclaimed[1], "seed_pin": pin, "pin": personal_pin},
                    )[0]

                pins = [value for value in ("672345", "765432", "823456") if value != pin][:2]
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    attempts = list(pool.map(compete, pins))
                require(
                    sorted(code for _, code in attempts) == [200, 400],
                    "Concurrent claims did not produce exactly one winner.",
                )
                winner = next(value for value, code in attempts if code == 200)
                require(
                    request("POST", "/api/session", {"name": unclaimed[1], "pin": winner})[0]
                    == 200,
                    "The new personal PIN could not sign in on the disposable copy.",
                )
                require(
                    request(
                        "POST",
                        "/api/claim",
                        {"name": unclaimed[1], "seed_pin": pin, "pin": pins[0]},
                    )[0]
                    == 400,
                    "A second claim replaced the personal PIN.",
                )
                result["claim_race"] = {"value": "passed"}
            with sqlite3.connect(copy) as connection:
                for row in participants:
                    if row[3] is not None:
                        require(
                            connection.execute(
                                "SELECT name_key,name,pin_salt,pin_hash FROM participants WHERE name_key=?",
                                (row[0],),
                            ).fetchone()
                            == row,
                            "An existing personal PIN hash changed.",
                        )
                require(
                    connection.execute(
                        "SELECT name_key,day FROM availability ORDER BY name_key,day"
                    ).fetchall()
                    == dates,
                    "Claim checks changed saved dates.",
                )
                restored_events = connection.execute(
                    "SELECT * FROM events WHERE id<=? ORDER BY id",
                    (max((row[0] for row in events), default=0),),
                ).fetchall()
                require(restored_events == events, "Claim checks changed old events.")
            after = database_state(copy)
            require(
                all(
                    after[name] == value
                    for name, value in initialized.items()
                    if name.startswith("trip_")
                ),
                "Claim checks changed private trip records.",
            )
            result["existing_pin_hashes_dates_events_and_trip_records"] = "preserved"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=10)
    require(
        database_state(database) == before,
        "The supplied restored database changed during the check.",
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(args.database, args.runtime.resolve(), json.load(sys.stdin))
        print(json.dumps(result))
    except CheckFailure as error:
        print(json.dumps({"data_checks": "failed", "cause": str(error)}))
        raise SystemExit(2) from None
    except Exception:
        print(
            json.dumps(
                {
                    "data_checks": "failed",
                    "cause": "The isolated Boys data check did not pass. No private records are printed.",
                }
            )
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
