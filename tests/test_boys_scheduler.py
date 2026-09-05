from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import sys
import threading
import time
from datetime import date, timedelta
from http.client import HTTPConnection
from pathlib import Path

import pytest
import yaml
from conftest import ROOT

PACKAGE = ROOT / "kubernetes/boys"
APP = PACKAGE / "app"
APPLICATION = ROOT / "playbooks/argocd/applications/web/boys/boys-application.yaml"
PROJECT = ROOT / "playbooks/argocd/applications/web/boys/boys-project.yaml"
CREW = [
    "Boris K",
    "Sergey Kiktev",
    "Max Edin",
    "Innok Mikhalev",
    "Alexey Pichulev",
    "Vitaly Borisov",
    "Eugene Kobyak",
    "Konstantin Pastbin",
    "Bronislav",
]


def load_server_module():
    spec = importlib.util.spec_from_file_location("boys_server", APP / "server.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(APP))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(APP))
    return module


def request(server, method: str, path: str, payload=None, cookie: str | None = None):
    headers = {}
    body = None
    if payload is not None:
        body = json.dumps(payload)
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie

    connection = HTTPConnection(*server.server_address, timeout=3)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    response_headers = dict(response.getheaders())
    connection.close()
    data = json.loads(raw) if raw else None
    return response.status, response_headers, data


def login(server, name: str, pin: str = "2468") -> tuple[str, dict]:
    status, headers, payload = request(
        server,
        "POST",
        "/api/session",
        {"name": name, "pin": pin},
    )
    assert status == 200
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    assert "HttpOnly" in headers["Set-Cookie"]
    assert "SameSite=Strict" in headers["Set-Cookie"]
    assert "Secure" in headers["Set-Cookie"]
    return cookie, payload


def claim(server, name: str, pin: str = "2468", seed_pin: str = "1357") -> tuple[str, dict]:
    status, headers, payload = request(
        server,
        "POST",
        "/api/claim",
        {"name": name, "seed_pin": seed_pin, "pin": pin},
    )
    assert status == 200
    return headers["Set-Cookie"].split(";", 1)[0], payload


def test_crew_claim_and_availability_round_trip(tmp_path: Path) -> None:
    module = load_server_module()
    app = module.BoysApp(
        database_path=tmp_path / "boys.sqlite3",
        seed_pin="1357",
        session_key=b"test-session-key-that-is-long-enough",
        assets_dir=APP,
    )
    server = module.make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        status, _, payload = request(server, "GET", "/healthz")
        assert (status, payload) == (200, {"ok": True})

        status, _, payload = request(server, "GET", "/api/crew")
        assert status == 200
        assert payload == {"crew": [{"name": name, "claimed": False} for name in CREW]}
        assert request(server, "GET", "/api/session")[2] == {"authenticated": False}

        status, headers, payload = request(
            server,
            "POST",
            "/api/session",
            {"name": "Boris K", "pin": "2468"},
        )
        assert status == 401
        assert "Set-Cookie" not in headers
        assert payload == {"error": "Claim this name first."}

        status, _, payload = request(
            server,
            "POST",
            "/api/claim/check",
            {"name": "Boris K", "seed_pin": "wrong"},
        )
        assert status == 401
        assert payload == {"error": "The crew PIN is not correct."}

        status, _, payload = request(
            server,
            "POST",
            "/api/claim/check",
            {"name": "Boris K", "seed_pin": "1357"},
        )
        assert status == 200
        assert payload == {"name": "Boris K"}
        assert request(server, "GET", "/api/crew")[2]["crew"][0] == {
            "name": "Boris K",
            "claimed": False,
        }

        status, _, payload = request(
            server,
            "POST",
            "/api/claim",
            {"name": "Boris K", "seed_pin": "wrong", "pin": "2468"},
        )
        assert status == 401
        assert payload == {"error": "The crew PIN is not correct."}

        status, _, payload = request(
            server,
            "POST",
            "/api/claim",
            {"name": "Boris K", "seed_pin": "1357", "pin": "1357"},
        )
        assert status == 400
        assert payload == {"error": "Choose a different PIN."}

        boris_cookie, payload = claim(server, "Boris K")
        assert payload == {"name": "Boris K"}
        assert request(server, "GET", "/api/session", cookie=boris_cookie)[2] == {
            "authenticated": True
        }
        status, _, payload = request(server, "GET", "/api/events", cookie=boris_cookie)
        assert status == 200
        assert [(event["name"], event["action"]) for event in payload["events"]] == [
            ("Boris K", "claimed")
        ]
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", payload["events"][0]["at"]
        )
        with app.connect() as connection:
            salt, pin_hash = connection.execute(
                "SELECT pin_salt, pin_hash FROM participants WHERE name_key = ?",
                ("boris k",),
            ).fetchone()
        assert len(salt) == 16
        assert len(pin_hash) == 32
        assert b"2468" not in (salt, pin_hash)

        status, _, payload = request(server, "GET", "/api/crew")
        assert status == 200
        assert payload["crew"][0] == {"name": "Boris K", "claimed": True}

        status, _, payload = request(
            server,
            "POST",
            "/api/claim",
            {"name": "Boris K", "seed_pin": "1357", "pin": "5678"},
        )
        assert status == 400
        assert payload == {"error": "This name is already claimed."}

        status, _, payload = request(
            server,
            "POST",
            "/api/session",
            {"name": "Boris K", "pin": "wrong"},
        )
        assert status == 401
        assert payload == {"error": "The PIN is not correct."}

        _, payload = login(server, "Boris K")
        assert payload == {"name": "Boris K"}

        status, _, payload = request(
            server,
            "POST",
            "/api/session",
            {"name": "Not in crew", "pin": "2468"},
        )
        assert status == 401
        assert payload == {"error": "Choose your crew name."}

        sergey_cookie, _ = claim(server, "Sergey Kiktev", pin="5678")

        first_day = (date.today() + timedelta(days=4)).isoformat()
        overlap_day = (date.today() + timedelta(days=8)).isoformat()
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {
                    "dates": [first_day, overlap_day, overlap_day],
                    "expected_revision": app.availability("Boris K")["revision"],
                },
                boris_cookie,
            )[0]
            == 200
        )
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {
                    "dates": [overlap_day],
                    "expected_revision": app.availability("Sergey Kiktev")["revision"],
                },
                sergey_cookie,
            )[0]
            == 200
        )

        status, _, payload = request(server, "GET", "/api/availability", cookie=boris_cookie)
        assert status == 200
        assert payload["me"] == "Boris K"
        participants = {item["name"]: item for item in payload["participants"]}
        assert list(participants) == sorted(CREW, key=str.casefold)
        assert participants["Boris K"] == {
            "name": "Boris K",
            "claimed": True,
            "dates": [first_day, overlap_day],
        }
        assert participants["Sergey Kiktev"] == {
            "name": "Sergey Kiktev",
            "claimed": True,
            "dates": [overlap_day],
        }
        assert all(
            not participant["claimed"] and not participant["dates"]
            for name, participant in participants.items()
            if name not in {"Boris K", "Sergey Kiktev"}
        )

        status, _, payload = request(server, "GET", "/api/events", cookie=boris_cookie)
        assert status == 200
        assert [
            (event["name"], event["action"], event.get("days")) for event in payload["events"]
        ] == [
            ("Sergey Kiktev", "availability", 1),
            ("Boris K", "availability", 2),
            ("Sergey Kiktev", "claimed", None),
            ("Boris K", "claimed", None),
        ]

        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {
                    "dates": [overlap_day],
                    "expected_revision": app.availability("Sergey Kiktev")["revision"],
                },
                sergey_cookie,
            )[0]
            == 200
        )
        assert request(server, "GET", "/api/events", cookie=boris_cookie)[2] == payload

        status, _, payload = request(
            server,
            "PUT",
            "/api/availability",
            {"dates": ["2020-01-01"], "expected_revision": app.availability("Boris K")["revision"]},
            boris_cookie,
        )
        assert status == 400
        assert payload == {"error": "Select dates from today through the next year."}

        status, headers, _ = request(server, "GET", "/api/availability")
        assert status == 401
        assert headers["Content-Security-Policy"].startswith("default-src 'self'")
        assert request(server, "GET", "/api/events")[0] == 401

        status, _, payload = request(
            server,
            "GET",
            "/api/availability",
            cookie="boys_session=not-a-valid-session",
        )
        assert status == 401
        assert payload == {"error": "Enter your name and PIN."}

        old_token = module.encode_token(
            {
                "expires": int(time.time()) + 60,
                "name": "Boris K",
                "name_key": "boris k",
            },
            b"test-session-key-that-is-long-enough",
        )
        assert (
            request(
                server,
                "GET",
                "/api/availability",
                cookie=f"boys_session={old_token}",
            )[0]
            == 401
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_existing_database_is_migrated_without_exposing_old_names(tmp_path: Path) -> None:
    module = load_server_module()
    database = tmp_path / "boys.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE participants (name_key TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE availability (
                name_key TEXT NOT NULL REFERENCES participants(name_key) ON DELETE CASCADE,
                day TEXT NOT NULL,
                PRIMARY KEY (name_key, day)
            );
            INSERT INTO participants VALUES ('old name', 'Old Name');
            """
        )

    app = module.BoysApp(
        database_path=database,
        seed_pin="1357",
        session_key=b"test-session-key-that-is-long-enough",
        assets_dir=APP,
    )

    with app.connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(participants)")}
        assert {"pin_salt", "pin_hash"} <= columns
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'events'"
        ).fetchone() == ("events",)
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone() == (0,)
        assert connection.execute(
            "SELECT name FROM participants WHERE name_key = 'old name'"
        ).fetchone() == ("Old Name",)
    assert app.crew() == [{"name": name, "claimed": False} for name in CREW]
    assert [item["name"] for item in app.availability("Boris K")["participants"]] == sorted(
        CREW, key=str.casefold
    )


def test_existing_claims_start_the_event_log_with_current_state(tmp_path: Path) -> None:
    module = load_server_module()
    database = tmp_path / "boys.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE participants (
                name_key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pin_salt BLOB,
                pin_hash BLOB
            );
            CREATE TABLE availability (
                name_key TEXT NOT NULL REFERENCES participants(name_key) ON DELETE CASCADE,
                day TEXT NOT NULL,
                PRIMARY KEY (name_key, day)
            );
            INSERT INTO participants VALUES ('boris k', 'Boris K', X'01', X'02');
            INSERT INTO participants VALUES (
                'innok mikhalev', 'Innok Mikhalev', X'03', X'04'
            );
            """
        )
        connection.executemany(
            "INSERT INTO availability VALUES ('innok mikhalev', ?)",
            ((f"2026-09-{day:02d}",) for day in range(1, 20)),
        )

    app = module.BoysApp(
        database_path=database,
        seed_pin="1357",
        session_key=b"test-session-key-that-is-long-enough",
        assets_dir=APP,
    )
    expected = [
        {
            "name": "Innok Mikhalev",
            "action": "baseline",
            "days": 19,
        },
        {
            "name": "Boris K",
            "action": "baseline",
            "days": 0,
        },
    ]
    assert app.events() == expected

    restarted = module.BoysApp(
        database_path=database,
        seed_pin="1357",
        session_key=b"test-session-key-that-is-long-enough",
        assets_dir=APP,
    )
    assert restarted.events() == expected


def test_gitops_package_has_persistence_and_a_narrow_public_path() -> None:
    import subprocess

    result = subprocess.run(
        ["kubectl", "kustomize", str(PACKAGE)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    resources = [item for item in yaml.safe_load_all(result.stdout) if item]
    by_kind_name = {(item["kind"], item["metadata"]["name"]): item for item in resources}

    namespace = by_kind_name[("Namespace", "boys")]
    assert {"Prune=false", "Delete=false"} <= set(
        namespace["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
    )
    assert namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"

    pvc = by_kind_name[("PersistentVolumeClaim", "boys-data")]
    assert {"Prune=false", "Delete=false"} <= set(
        pvc["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
    )
    assert pvc["spec"]["storageClassName"] == "longhorn"

    ingress = by_kind_name[("Ingress", "boys")]
    assert ingress["spec"]["tls"] == [{"hosts": ["boys.soyspray.vip"], "secretName": "boys-tls"}]
    assert "external-dns.alpha.kubernetes.io/hostname" not in ingress["metadata"].get(
        "annotations", {}
    )

    deployments = {
        item["metadata"]["name"]: item for item in resources if item["kind"] == "Deployment"
    }
    assert set(deployments) == {"boys", "boys-cloudflared"}
    app_container = deployments["boys"]["spec"]["template"]["spec"]["containers"][0]
    assert app_container["image"].startswith("ghcr.io/kpoxo6op/boys@sha256:")
    assert not any(mount["mountPath"] == "/app" for mount in app_container["volumeMounts"])
    env = {item["name"]: item for item in app_container["env"]}
    assert env["BOYS_DATABASE"]["value"] == "/data/boys.sqlite3"
    for name, key in (("BOYS_PIN", "pin"), ("BOYS_SESSION_KEY", "session-key")):
        assert env[name]["valueFrom"]["secretKeyRef"] == {"name": "boys-runtime", "key": key}
        assert "value" not in env[name]
    assert env["BOYS_TRIP_SEED_FILE"]["value"] == "/run/trip/seed.json"
    seed_mount = next(item for item in app_container["volumeMounts"] if item["name"] == "trip-seed")
    assert seed_mount["mountPath"] == "/run/trip" and seed_mount["readOnly"] is True
    pod = deployments["boys"]["spec"]["template"]["spec"]
    seed_volume = next(item for item in pod["volumes"] if item["name"] == "trip-seed")
    assert seed_volume["secret"] == {"secretName": "boys-trip-seed", "defaultMode": 0o440}
    assert pod["securityContext"]["fsGroup"] == 1000
    assert deployments["boys"]["spec"]["strategy"]["type"] == "Recreate"

    for deployment in deployments.values():
        pod = deployment["spec"]["template"]["spec"]
        assert pod["automountServiceAccountToken"] is False
        assert pod["securityContext"]["runAsNonRoot"] is True
        for container in pod["containers"]:
            assert "@sha256:" in container["image"]
            assert container["securityContext"]["allowPrivilegeEscalation"] is False
            assert container["securityContext"]["readOnlyRootFilesystem"] is True
            assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]

    policies = [item for item in resources if item["kind"] == "NetworkPolicy"]
    assert any(item["metadata"]["name"] == "boys-default-deny" for item in policies)
    assert ("GlobalNetworkPolicy", "boys-cloudflared-host-boundary") in by_kind_name
    assert len([item for item in resources if item["kind"] == "HostEndpoint"]) == 3


def test_argocd_role_owns_secrets_and_revision_selection() -> None:
    application = yaml.safe_load(APPLICATION.read_text())
    project = yaml.safe_load(PROJECT.read_text())
    enabled = (ROOT / "roles/apps/boys/tasks/enabled.yml").read_text()
    disabled = (ROOT / "roles/apps/boys/tasks/disabled.yml").read_text()
    defaults = (ROOT / "roles/apps/boys/defaults/main.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()
    playbook = (ROOT / "playbooks/deploy-argocd-apps.yml").read_text()

    assert application["spec"]["source"] == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "HEAD",
        "path": "kubernetes/boys",
        "kustomize": {
            "patches": [
                {
                    "target": {"kind": "Deployment", "name": "boys"},
                    "patch": (
                        "apiVersion: apps/v1\n"
                        "kind: Deployment\n"
                        "metadata:\n"
                        "  name: boys\n"
                        "spec:\n"
                        "  template:\n"
                        "    metadata:\n"
                        "      annotations:\n"
                        "        soyspray.vip/runtime-secret-resource-version: "
                        '"BOYS_RUNTIME_SECRET_RESOURCE_VERSION"'
                    ),
                }
            ]
        },
    }
    assert application["spec"]["project"] == "boys"
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "boys"}
    ]
    allowed_kinds = {item["kind"] for item in project["spec"]["namespaceResourceWhitelist"]}
    assert "PersistentVolumeClaim" in allowed_kinds
    assert "Secret" not in allowed_kinds

    assert "boys_enabled: true" in defaults
    assert "boys_target_revision: HEAD" in defaults
    assert "boys_runtime_secret" in enabled
    assert "BOYS_RUNTIME_SECRET_RESOURCE_VERSION" in enabled
    assert "resourceVersion" in enabled
    assert "targetRevision" in enabled
    assert disabled.index("Quiesce the boys Argo application") < disabled.index(
        "Remove the boys runtime secrets"
    )
    assert disabled.index("Remove the boys runtime secrets") < disabled.index(
        "Remove the boys Argo application"
    )
    assert "role: apps/boys" in playbook
    assert "BOYS_REVISION ?= HEAD" in makefile
    assert "boys: go" in makefile
    assert "--tags boys" in makefile


@pytest.fixture
def saving_app(tmp_path):
    module = load_server_module()
    app = module.BoysApp(
        tmp_path / "boys.sqlite3", "1357", b"test-session-key-that-is-long-enough", APP
    )
    _, token = app.claim("Boris K", "1357", "2468", "test")
    return module, app, app.session("boys_session=" + token)


def test_saving_preserves_history_and_rejects_invented_past_dates(saving_app):
    module, app, session = saving_app
    past = (date.today() - timedelta(days=30)).isoformat()
    future = (date.today() + timedelta(days=4)).isoformat()
    with app.connect() as connection:
        connection.execute("INSERT INTO availability VALUES (?, ?)", (session["name_key"], past))
        identity = connection.execute("SELECT * FROM participants").fetchall()
    before = app.availability(session["name"])
    saved = app.save_availability(session, [future], before["revision"])
    assert next(p["dates"] for p in saved["participants"] if p["name"] == session["name"]) == [
        past,
        future,
    ]
    emptied = app.save_availability(session, [], saved["revision"])
    assert next(p["dates"] for p in emptied["participants"] if p["name"] == session["name"]) == [
        past
    ]
    events = app.events()
    with pytest.raises(ValueError):
        app.save_availability(session, ["2000-01-01"], emptied["revision"])
    assert app.events() == events
    with app.connect() as connection:
        assert connection.execute("SELECT * FROM participants").fetchall() == identity
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_concurrent_availability_writes_have_one_winner(saving_app):
    module, app, session = saving_app
    revision = app.availability(session["name"])["revision"]
    barrier = threading.Barrier(2)
    results = []

    def save(offset):
        barrier.wait(timeout=3)
        try:
            results.append(
                app.save_availability(
                    session, [(date.today() + timedelta(days=offset)).isoformat()], revision
                )
            )
        except module.EditConflict:
            results.append("conflict")

    threads = [threading.Thread(target=save, args=(offset,)) for offset in (2, 3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert results.count("conflict") == 1
    winner = next(item for item in results if item != "conflict")
    assert app.availability(session["name"]) == winner
    assert len([event for event in app.events() if event["action"] == "availability"]) == 1


def test_availability_conflicts_return_409_without_changing_data(saving_app):
    module, app, session = saving_app
    server = module.make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cookie, _ = login(server, session["name"])
        initial = request(server, "GET", "/api/availability", cookie=cookie)[2]
        dates = [(date.today() + timedelta(days=2)).isoformat()]
        assert request(server, "PUT", "/api/availability", {"dates": dates}, cookie)[0] == 409
        status, _, saved = request(
            server,
            "PUT",
            "/api/availability",
            {"dates": dates, "expected_revision": initial["revision"]},
            cookie,
        )
        assert status == 200
        events = app.events()
        for revision in (initial["revision"], None, 1, "bad"):
            assert (
                request(
                    server,
                    "PUT",
                    "/api/availability",
                    {"dates": [], "expected_revision": revision},
                    cookie,
                )[0]
                == 409
            )
        assert app.availability(session["name"]) == saved
        assert app.events() == events
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {"dates": [], "expected_revision": saved["revision"]},
            )[0]
            == 401
        )
        # An idempotent retry does not add an event.
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {"dates": dates, "expected_revision": saved["revision"]},
                cookie,
            )[0]
            == 200
        )
        assert app.events() == events
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_availability_and_event_roll_back_together(saving_app):
    _, app, session = saving_app
    before = app.availability(session["name"])
    events = app.events()
    with app.connect() as connection:
        connection.execute(
            "CREATE TRIGGER fail_event BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT, 'test audit failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        app.save_availability(session, [date.today().isoformat()], before["revision"])
    assert app.availability(session["name"]) == before
    assert app.events() == events


def test_concurrent_claims_keep_one_personal_pin_and_one_event(saving_app):
    _, app, _ = saving_app
    barrier = threading.Barrier(2)
    results = []

    def claim_once(pin):
        barrier.wait(timeout=3)
        try:
            app.claim("Max Edin", "1357", pin, pin)
            results.append(pin)
        except ValueError:
            results.append("conflict")

    threads = [threading.Thread(target=claim_once, args=(pin,)) for pin in ("3456", "5678")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert results.count("conflict") == 1
    winner = next(pin for pin in results if pin != "conflict")
    name, token = app.login("Max Edin", winner, "login")
    assert name == "Max Edin"
    assert app.session("boys_session=" + token)
    with pytest.raises(ValueError):
        app.claim("Max Edin", "1357", "6789", "reset")
    with pytest.raises(PermissionError):
        app.login("Max Edin", "1357", "crew-login")
    assert len([event for event in app.events() if event["name"] == name]) == 1
