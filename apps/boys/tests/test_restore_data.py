import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from apps.boys.check_restore import database_state

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "kubernetes/boys/app"
INPUTS = {"boys_pin": "1357", "boys_session_key": "synthetic-recovery-key-with-no-live-access"}


@pytest.fixture
def restored(tmp_path):
    sys.path.insert(0, str(RUNTIME))
    try:
        spec = importlib.util.spec_from_file_location("boys_fixture", RUNTIME / "server.py")
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
    finally:
        sys.path.remove(str(RUNTIME))
    path = tmp_path / "boys.sqlite3"
    app = runtime.BoysApp(path, INPUTS["boys_pin"], INPUTS["boys_session_key"].encode())
    holder = sqlite3.connect(path)
    holder.execute("PRAGMA wal_autocheckpoint=0")
    member = runtime.CREW[0]
    app.claim(member, INPUTS["boys_pin"], "5678", "fixture")
    holder.execute("INSERT INTO availability VALUES(?, ?)", (member.casefold(), "2020-01-02"))
    holder.commit()
    seed = tmp_path / "seed.json"
    seed.write_text(
        json.dumps(
            {
                "id": "example-trip",
                "document": {
                    "destination": {"name": "Synthetic recovery destination"},
                    "dates": {"options": [], "selected": None},
                    "budget": {"min_cents": None, "max_cents": None},
                    "accommodation": {"candidates": [], "selected": None, "paying_people": None},
                    "call": {"at": None, "timezone": None, "url": ""},
                },
            }
        )
    )
    app.trips.seed(seed)
    yield path, app, runtime
    holder.close()


def run_check(database):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "apps/boys/check_restore.py"),
            "--database",
            str(database),
            "--runtime",
            str(RUNTIME),
        ],
        input=json.dumps(INPUTS),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert INPUTS["boys_session_key"] not in result.stdout + result.stderr
    assert "Synthetic recovery destination" not in result.stdout + result.stderr
    return result.returncode, json.loads(result.stdout)


def test_restored_wal_dates_trip_and_pin_hashes_survive_disposable_claim_checks(restored):
    database, _, _ = restored
    assert database.with_name(database.name + "-wal").stat().st_size > 0
    before = database_state(database)
    code, report = run_check(database)
    assert code == 0, report
    assert report["data_checks"] == "passed"
    assert report["legacy_session_format"] == {"value": "passed"}
    assert report["claim_race"] == {"value": "passed"}
    assert report["rows"]["availability"] == 1
    assert report["rows"]["trip_documents"] == 1
    assert report["rows"]["trip_audit"] == 1
    assert report["human_personal_pin"]["value"] == "unknown"
    assert report["existing_browser_cookie"]["value"] == "unknown"
    assert database_state(database) == before


def test_a_fully_claimed_crew_reports_the_unavailable_race_check(restored):
    database, app, runtime = restored
    for member in runtime.CREW[1:]:
        app.claim(member, INPUTS["boys_pin"], "5678", "fixture")
    before = database_state(database)
    code, report = run_check(database)
    assert code == 0, report
    assert report["claim_race"] == {
        "value": "unknown",
        "cause": "The backup has no unclaimed member.",
    }
    assert database_state(database) == before


@pytest.mark.parametrize("damage", ["not-sqlite", "empty", "missing-crew"])
def test_an_unusable_backup_cannot_become_a_success_report(tmp_path, restored, damage):
    source, _, _ = restored
    path = tmp_path / "invalid.sqlite3"
    if damage == "not-sqlite":
        path.write_bytes(b"not a database")
    elif damage == "empty":
        sqlite3.connect(path).close()
    else:
        with sqlite3.connect(source) as origin, sqlite3.connect(path) as target:
            origin.backup(target)
        with sqlite3.connect(path) as connection:
            connection.execute("DELETE FROM participants WHERE pin_hash IS NULL")
    before = path.read_bytes()
    code, report = run_check(path)
    assert code == 2
    assert report["data_checks"] == "failed"
    assert path.read_bytes() == before
