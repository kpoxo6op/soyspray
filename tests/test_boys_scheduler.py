from __future__ import annotations

import importlib.util
import json
import threading
from datetime import date, timedelta
from http.client import HTTPConnection
from pathlib import Path

import yaml
from conftest import ROOT

PACKAGE = ROOT / "kubernetes/boys"
APP = PACKAGE / "app"
APPLICATION = ROOT / "playbooks/argocd/applications/web/boys/boys-application.yaml"
PROJECT = ROOT / "playbooks/argocd/applications/web/boys/boys-project.yaml"


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


def login(server, name: str, pin: str = "246810") -> tuple[str, dict]:
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


def test_shared_pin_and_availability_round_trip(tmp_path: Path) -> None:
    module = load_server_module()
    app = module.BoysApp(
        database_path=tmp_path / "boys.sqlite3",
        pin="246810",
        session_key=b"test-session-key-that-is-long-enough",
        assets_dir=APP,
    )
    server = module.make_server(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        status, _, payload = request(server, "GET", "/healthz")
        assert (status, payload) == (200, {"ok": True})

        status, headers, payload = request(
            server,
            "POST",
            "/api/session",
            {"name": "Alice", "pin": "wrong"},
        )
        assert status == 401
        assert "Set-Cookie" not in headers
        assert payload == {"error": "The PIN is not correct."}

        alice_cookie, payload = login(server, "  Alice  ")
        assert payload == {"name": "Alice"}
        bob_cookie, _ = login(server, "Bob")

        first_day = (date.today() + timedelta(days=4)).isoformat()
        overlap_day = (date.today() + timedelta(days=8)).isoformat()
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {"dates": [first_day, overlap_day, overlap_day]},
                alice_cookie,
            )[0]
            == 200
        )
        assert (
            request(
                server,
                "PUT",
                "/api/availability",
                {"dates": [overlap_day]},
                bob_cookie,
            )[0]
            == 200
        )

        status, _, payload = request(server, "GET", "/api/availability", cookie=alice_cookie)
        assert status == 200
        assert payload == {
            "me": "Alice",
            "participants": [
                {"name": "Alice", "dates": [first_day, overlap_day]},
                {"name": "Bob", "dates": [overlap_day]},
            ],
        }

        status, _, payload = request(
            server,
            "PUT",
            "/api/availability",
            {"dates": ["2020-01-01"]},
            alice_cookie,
        )
        assert status == 400
        assert payload == {"error": "Select dates from today through the next year."}

        status, headers, _ = request(server, "GET", "/api/availability")
        assert status == 401
        assert headers["Content-Security-Policy"].startswith("default-src 'self'")

        status, _, payload = request(
            server,
            "GET",
            "/api/availability",
            cookie="boys_session=not-a-valid-session",
        )
        assert status == 401
        assert payload == {"error": "Enter your name and PIN."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_scheduler_frontend_is_local_and_shows_calendar_stripes() -> None:
    html = (APP / "index.html").read_text()
    script = (APP / "app.js").read_text()
    styles = (APP / "styles.css").read_text()

    assert "Boys calendar" in html
    assert 'name="name"' in html
    assert 'inputmode="numeric"' in html
    assert "https://" not in html
    assert "calendar-grid" in html
    assert "availability-stripe" in script
    assert "aria-pressed" in script
    assert "--background:" in styles
    assert ".availability-stripe" in styles
    assert "mix-blend-mode: multiply" in styles


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
    assert namespace["metadata"]["annotations"]["argocd.argoproj.io/sync-options"] == "Delete=false"
    assert namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"

    pvc = by_kind_name[("PersistentVolumeClaim", "boys-data")]
    assert pvc["metadata"]["annotations"]["argocd.argoproj.io/sync-options"] == "Delete=false"
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
    assert app_container["image"].startswith("python:3.13-alpine@sha256:")
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
