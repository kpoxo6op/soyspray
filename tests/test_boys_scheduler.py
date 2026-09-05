from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import threading
import time
from datetime import date, timedelta
from http.client import HTTPConnection
from pathlib import Path

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
    spec.loader.exec_module(module)
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
                {"dates": [first_day, overlap_day, overlap_day]},
                boris_cookie,
            )[0]
            == 200
        )
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {"dates": [overlap_day]},
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
                {"dates": [overlap_day]},
                sergey_cookie,
            )[0]
            == 200
        )
        assert request(server, "GET", "/api/events", cookie=boris_cookie)[2] == payload

        status, _, payload = request(
            server,
            "PUT",
            "/api/availability",
            {"dates": ["2020-01-01"]},
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


def test_scheduler_frontend_is_local_and_shows_calendar_stripes() -> None:
    html = (APP / "index.html").read_text()
    script = (APP / "app.js").read_text()
    styles = (APP / "styles.css").read_text()
    events_html = (APP / "events.html").read_text()
    events_script = (APP / "events.js").read_text()

    assert "Boys calendar" in html
    assert '<select id="name"' in html
    assert 'inputmode="numeric"' in html
    assert re.findall(r'https://[^"\s]+', html) == ["https://t.me/borex69"]
    forms = {
        form_id: re.search(rf'<form id="{form_id}".*?</form>', html, re.DOTALL).group()
        for form_id in ("name-form", "login-form", "crew-pin-form", "personal-pin-form")
    }
    assert forms["name-form"].count("<select") == 1
    assert 'type="password"' not in forms["name-form"]
    for form_id in ("login-form", "crew-pin-form", "personal-pin-form"):
        assert forms[form_id].count('type="password"') == 1
        assert "<select" not in forms[form_id]
    for form in forms.values():
        assert form.count('class="button button-primary"') == 1
    assert 'id="claim-form"' not in html
    assert 'id="claim-button"' not in html
    assert "Forgot PIN?" in html
    assert "/api/crew" in script
    assert "/api/claim/check" in script
    assert "/api/claim" in script
    assert "· claim" not in script
    assert "calendar-grid" in html
    assert "Each boy has one color." not in html
    assert "Select your dates." in html
    assert 'href="/events.html"' in html
    assert 'id="event-list"' in events_html
    assert 'href="/"' in events_html
    assert "Back to calendar" in events_html
    assert "Newest first." in events_html
    assert "/api/events" in events_script
    assert "Set ${event.days} available" in events_script
    assert 'event.action === "claimed"' in events_script
    assert 'event.action === "baseline"' in events_script
    assert 'time.textContent = "Before log"' in events_script
    assert "setInterval(loadEvents, 5000)" in events_script
    assert "availability-stripe" in script
    assert "is-selected" not in script
    assert "is-selected" not in styles
    assert '"no dates"' in script
    assert '"unclaimed"' in script
    assert '${days === 1 ? "day" : "days"}' in script
    assert "aria-pressed" in script
    assert set(re.findall(r"<h([1-6])", html)) == {"1", "2"}
    assert "--background:" in styles
    assert ".availability-stripe" in styles
    assert "mix-blend-mode" not in styles
    color_classes = dict(re.findall(r'^\s+"([^"]+)": "(boy-[^"]+)",$', script, re.MULTILINE))
    assert set(color_classes) == set(CREW)
    assert len(set(color_classes.values())) == len(CREW)
    boy_colors = re.findall(r"--boy-[a-z-]+:\s*(#[0-9a-fA-F]{6})", styles)
    assert len(boy_colors) == len(CREW)
    assert len(set(boy_colors)) == len(CREW)
    boy_patterns = re.findall(r"--boy-pattern:\s*([^;]+);", styles)
    assert len(boy_patterns) == len(CREW)
    assert len(set(boy_patterns)) == len(CREW)
    assert "background-image: var(--boy-pattern)" in styles
    assert "radial-gradient" in styles
    assert "repeating-linear-gradient" in styles
    assert "colorIndex" not in script
    assert "stripe-0" not in styles
    assert "stripe-1" not in styles
    assert ".card" not in styles
    assert "box-shadow" not in styles
    assert styles.count("font-family:") == 1


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
    app_config = next(item for item in resources if item["kind"] == "ConfigMap")
    assert {"server.py", "index.html", "app.js", "styles.css", "events.html", "events.js"} <= set(
        app_config["data"]
    )
    assert set(deployments) == {"boys", "boys-cloudflared"}
    app_container = deployments["boys"]["spec"]["template"]["spec"]["containers"][0]
    assert app_container["image"].startswith("ghcr.io/kpoxo6op/boys@sha256:")
    assert not any(mount["mountPath"] == "/app" for mount in app_container["volumeMounts"])
    assert {item["name"] for item in app_container["env"]} == {
        "BOYS_DATABASE",
        "BOYS_PIN",
        "BOYS_SESSION_KEY",
    }
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
    assert "BOYS_PIN" in enabled
    assert "BOYS_SESSION_KEY" in enabled
    assert "BOYS_CLOUDFLARED_TOKEN" in enabled
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
