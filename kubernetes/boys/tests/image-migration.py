"""Check migration and rollback on a disposable Docker volume."""

import hashlib
import http.cookiejar
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

DATA = Path("/data")
MODE = sys.argv[1]
BASE = "http://127.0.0.1:8080"
jar = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(path, payload=None, cookie=None):
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    data = json.dumps(payload).encode() if payload is not None else None
    with client.open(
        urllib.request.Request(BASE + path, data=data, headers=headers), timeout=5
    ) as response:
        return json.load(response)


def fingerprint(connection):
    result = {}
    for table in ("participants", "availability", "events"):
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY 1,2").fetchall()
        data = json.dumps(
            rows, default=lambda value: value.hex(), ensure_ascii=False, separators=(",", ":")
        )
        result[table] = {
            "rows": len(rows),
            "sha256": hashlib.sha256(data.encode()).hexdigest(),
            "schema": connection.execute(
                "SELECT sql FROM sqlite_schema WHERE name=?", (table,)
            ).fetchone()[0],
        }
    assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return result


for attempt in range(40):
    try:
        if request("/ready")["ready"]:
            break
    except urllib.error.URLError:
        if attempt == 39:
            raise
    time.sleep(0.25)

if MODE == "record":
    request("/api/session", {"name": "Boris K", "pin": "5678"})
    cookie = "; ".join(f"{item.name}={item.value}" for item in jar)
    with sqlite3.connect(DATA / "boys.sqlite3") as connection:
        connection.executemany(
            "INSERT INTO availability VALUES('boris k',?)",
            [("2020-01-02",), ((date.today() + timedelta(days=7)).isoformat(),)],
        )
        connection.execute(
            "INSERT INTO events(name_key,action,available_days) VALUES('boris k','availability',2)"
        )
    with sqlite3.connect(DATA / "boys.sqlite3") as connection:
        baseline = {
            "tables": fingerprint(connection),
            "cookie": cookie,
            "has_trip_schema": bool(
                connection.execute(
                    "SELECT 1 FROM sqlite_schema WHERE name='trip_documents'"
                ).fetchone()
            ),
        }
    baseline["availability"] = request("/api/availability", cookie=cookie)
    baseline["events"] = request("/api/events", cookie=cookie)
    (DATA / "check-baseline.json").write_text(json.dumps(baseline))
    seed = {
        "id": "image-check",
        "document": {
            "destination": {"name": "Synthetic coast"},
            "dates": {
                "options": [
                    {
                        "id": "a",
                        "label": "Example",
                        "arrival": "2031-04-10",
                        "departure": "2031-04-13",
                    }
                ],
                "selected": None,
            },
            "budget": {"min_cents": None, "max_cents": None},
            "accommodation": {"candidates": [], "selected": None, "paying_people": None},
            "call": {"at": None, "timezone": None, "url": ""},
        },
    }
    (DATA / "check-seed.json").write_text(json.dumps(seed))
else:
    baseline = json.loads((DATA / "check-baseline.json").read_text())
    with sqlite3.connect(DATA / "boys.sqlite3") as connection:
        assert fingerprint(connection) == baseline["tables"]
    assert request("/api/availability", cookie=baseline["cookie"]) == baseline["availability"]
    assert request("/api/events", cookie=baseline["cookie"]) == baseline["events"]
    request("/api/session", {"name": "Boris K", "pin": "5678"})
    if MODE == "migrated":
        current = request("/api/trip")
        assert current["trip"]["document"]["destination"]["name"] == "Synthetic coast"
        assert current["responses"] == []
        if not baseline["has_trip_schema"]:
            backups = list(DATA.glob("boys.before-trip-*.sqlite3"))
            assert len(backups) == 1
            with sqlite3.connect(backups[0]) as backup:
                assert fingerprint(backup) == baseline["tables"]
                assert not backup.execute(
                    "SELECT 1 FROM sqlite_schema WHERE name='trip_documents'"
                ).fetchone()
    elif MODE != "rollback":
        raise ValueError("Unknown migration check mode")
print(f"Boys {MODE}: database integrity, identities, dates, events, and session checks passed.")
