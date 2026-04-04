from __future__ import annotations

import base64
import json
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import TestCase

from playbooks.argocd.applications.observability.splunk.pipeline.splunk_dashboard_pipeline import (
    DashboardPipeline,
    SplunkClient,
)


def sample_dashboard(title: str, body: str) -> str:
    return f"""<dashboard version="2" theme="light">
  <label>{title}</label>
  <definition><![CDATA[
{body}
  ]]></definition>
</dashboard>"""


class FakeSplunkState:
    def __init__(self) -> None:
        self.apps: dict[str, dict] = {}
        self.users: dict[str, dict] = {}
        self.dashboards: dict[tuple[str, str, str], str] = {}
        self.acls: dict[tuple[str, str, str], dict] = {}
        self.create_calls: list[str] = []
        self.update_calls: list[str] = []


class FakeSplunkHandler(BaseHTTPRequestHandler):
    server_version = "FakeSplunk/1.0"

    @property
    def state(self) -> FakeSplunkState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, *_args) -> None:
        return

    def _auth_ok(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        raw = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        username, _password = raw.split(":", 1)
        return username in {"admin", "svc_dashboards"}

    def _form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return urllib.parse.parse_qs(body, keep_blank_values=True)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self._auth_ok():
            self._send_json(401, {"messages": [{"text": "unauthorized"}]})
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/services/server/info":
            self._send_json(200, {"entry": [{"name": "server-info"}]})
            return

        if path.startswith("/services/apps/local/"):
            name = path.rsplit("/", 1)[-1]
            if name not in self.state.apps:
                self._send_json(404, {"messages": [{"text": "missing app"}]})
                return
            self._send_json(200, {"entry": [{"name": name}]})
            return

        if path.startswith("/services/authentication/users/"):
            name = path.rsplit("/", 1)[-1]
            if name not in self.state.users:
                self._send_json(404, {"messages": [{"text": "missing user"}]})
                return
            self._send_json(200, {"entry": [{"name": name}]})
            return

        if path.endswith("/data/ui/views"):
            owner, app = path.split("/")[2:4]
            entries = []
            for (dash_owner, dash_app, dash_name), xml_text in sorted(self.state.dashboards.items()):
                if (dash_owner, dash_app) == (owner, app):
                    entries.append({"name": dash_name, "content": {"eai:data": xml_text}})
            self._send_json(200, {"entry": entries})
            return

        if "/data/ui/views/" in path and not path.endswith("/acl"):
            owner, app = path.split("/")[2:4]
            name = path.rsplit("/", 1)[-1]
            key = (owner, app, name)
            if key not in self.state.dashboards:
                self._send_json(404, {"messages": [{"text": "missing dashboard"}]})
                return
            self._send_json(
                200,
                {"entry": [{"name": name, "content": {"eai:data": self.state.dashboards[key]}}]},
            )
            return

        self._send_json(404, {"messages": [{"text": "unknown endpoint"}]})

    def do_POST(self) -> None:  # noqa: N802
        if not self._auth_ok():
            self._send_json(401, {"messages": [{"text": "unauthorized"}]})
            return

        form = self._form()
        path = urllib.parse.urlparse(self.path).path

        if path == "/services/apps/local":
            name = form["name"][0]
            self.state.apps[name] = {
                "label": form.get("label", [name])[0],
                "description": form.get("description", [""])[0],
            }
            self._send_json(201, {"entry": [{"name": name}]})
            return

        if path.startswith("/services/apps/local/"):
            name = path.rsplit("/", 1)[-1]
            self.state.apps[name] = {
                "label": form.get("label", [name])[0],
                "description": form.get("description", [""])[0],
            }
            self._send_json(200, {"entry": [{"name": name}]})
            return

        if path == "/services/authentication/users":
            name = form["name"][0]
            self.state.users[name] = {
                "password": form["password"][0],
                "roles": form.get("roles", []),
            }
            self._send_json(201, {"entry": [{"name": name}]})
            return

        if path.startswith("/services/authentication/users/"):
            name = path.rsplit("/", 1)[-1]
            self.state.users[name] = {
                "password": form.get("password", [""])[0],
                "roles": form.get("roles", []),
            }
            self._send_json(200, {"entry": [{"name": name}]})
            return

        if path.endswith("/data/ui/views"):
            owner, app = path.split("/")[2:4]
            name = form["name"][0]
            xml_text = form["eai:data"][0]
            self.state.dashboards[(owner, app, name)] = xml_text
            self.state.create_calls.append(name)
            self._send_json(201, {"entry": [{"name": name}]})
            return

        if path.endswith("/acl"):
            parts = path.split("/")
            owner, app, name = parts[2], parts[3], parts[-2]
            self.state.acls[(owner, app, name)] = {
                "owner": form.get("owner", [""])[0],
                "sharing": form.get("sharing", [""])[0],
            }
            self._send_json(200, {"entry": [{"name": name}]})
            return

        if "/data/ui/views/" in path:
            owner, app = path.split("/")[2:4]
            name = path.rsplit("/", 1)[-1]
            self.state.dashboards[(owner, app, name)] = form["eai:data"][0]
            self.state.update_calls.append(name)
            self._send_json(200, {"entry": [{"name": name}]})
            return

        self._send_json(404, {"messages": [{"text": "unknown endpoint"}]})


class PipelineTests(TestCase):
    def setUp(self) -> None:
        self.state = FakeSplunkState()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSplunkHandler)
        self.server.state = self.state  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def pipeline(self) -> DashboardPipeline:
        return DashboardPipeline(
            admin_client=SplunkClient(self.base_url, "admin", "AdminPassword123!", verify_tls=True),
            service_client=SplunkClient(self.base_url, "svc_dashboards", "ServiceDashboards123!", verify_tls=True),
            service_account="svc_dashboards",
            service_password="ServiceDashboards123!",
            service_roles=["power"],
            app_name="soyspray_dashboards",
            app_label="Soyspray Dashboards",
            app_description="Example",
        )

    def test_bootstrap_creates_app_user_and_dashboards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "first.xml").write_text(sample_dashboard("First", '{"title":"First"}'), encoding="utf-8")
            (base / "second.xml").write_text(sample_dashboard("Second", '{"title":"Second"}'), encoding="utf-8")

            changes = self.pipeline().bootstrap(base)

        self.assertIn("created:first", changes)
        self.assertIn("created:second", changes)
        self.assertIn("soyspray_dashboards", self.state.apps)
        self.assertIn("svc_dashboards", self.state.users)
        self.assertEqual(self.state.acls[("svc_dashboards", "soyspray_dashboards", "first")]["sharing"], "app")

    def test_apply_skips_update_when_only_formatting_changes(self) -> None:
        self.state.dashboards[("svc_dashboards", "soyspray_dashboards", "first")] = (
            '<dashboard theme="light" version="2"><label>First</label>'
            '<definition><![CDATA[{"title":"First"}]]></definition></dashboard>'
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "first.xml").write_text(
                sample_dashboard(
                    "First",
                    '{\n  "title": "First"\n}',
                ),
                encoding="utf-8",
            )

            changes = self.pipeline().apply(base)

        self.assertEqual(["unchanged:first"], changes)
        self.assertEqual([], self.state.update_calls)

    def test_export_all_writes_dashboard_files(self) -> None:
        self.state.dashboards[("svc_dashboards", "soyspray_dashboards", "first")] = sample_dashboard(
            "First",
            '{"title":"First"}',
        )
        self.state.dashboards[("svc_dashboards", "soyspray_dashboards", "second")] = sample_dashboard(
            "Second",
            '{"title":"Second"}',
        )

        with tempfile.TemporaryDirectory() as tmp:
            exported = self.pipeline().export_all(tmp)
            exported_names = sorted(path.name for path in exported)
            first_text = Path(tmp, "first.xml").read_text(encoding="utf-8")

        self.assertEqual(["first.xml", "second.xml"], exported_names)
        self.assertIn("<label>First</label>", first_text)
