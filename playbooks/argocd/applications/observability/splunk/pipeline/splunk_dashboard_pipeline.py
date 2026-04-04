#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _strip(text: str | None) -> str:
    return (text or "").strip()


def _looks_like_json(text: str) -> bool:
    candidate = text.strip()
    return candidate.startswith("{") or candidate.startswith("[")


def _normalize_json_text(text: str) -> str:
    return json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))


def _canonicalize_xml(element: ET.Element) -> dict[str, Any]:
    normalized_text = _strip(element.text)
    if element.tag in {"definition", "meta"} and normalized_text and _looks_like_json(normalized_text):
        normalized_text = _normalize_json_text(normalized_text)

    return {
        "tag": element.tag,
        "attrib": dict(sorted(element.attrib.items())),
        "text": normalized_text,
        "children": [_canonicalize_xml(child) for child in list(element)],
    }


def normalize_dashboard_xml(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    return json.dumps(_canonicalize_xml(root), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class DashboardSpec:
    name: str
    path: Path
    raw_xml: str
    canonical_xml: str


class SplunkApiError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class SplunkClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        verify_tls: bool = False,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.ssl_context = None if verify_tls else ssl._create_unverified_context()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        form: list[tuple[str, str]] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> Any:
        request_params = {"output_mode": "json"}
        if params:
            request_params.update(params)

        url = f"{self.base_url}{path}"
        url = f"{url}?{urllib.parse.urlencode(request_params, doseq=True)}"

        data = None
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii"),
            "Accept": "application/json",
        }
        if form is not None:
            data = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
                context=self.ssl_context,
            ) as response:
                payload = response.read().decode("utf-8")
                if response.status not in expected:
                    raise SplunkApiError(
                        response.status,
                        f"{method} {path} returned unexpected status {response.status}",
                    )
                if not payload:
                    return {}
                return json.loads(payload)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            raise SplunkApiError(
                error.code,
                f"{method} {path} failed with {error.code}: {body[:500]}",
            ) from error

    def exists(self, path: str) -> bool:
        try:
            self.request("GET", path)
            return True
        except SplunkApiError as error:
            if error.status == 404:
                return False
            raise

    def ensure_app(self, name: str, label: str, description: str) -> None:
        if self.exists(f"/services/apps/local/{name}"):
            self.request(
                "POST",
                f"/services/apps/local/{name}",
                form=[
                    ("label", label),
                    ("description", description),
                    ("visible", "true"),
                ],
            )
            return

        self.request(
            "POST",
            "/services/apps/local",
            form=[
                ("name", name),
                ("label", label),
                ("description", description),
                ("visible", "true"),
            ],
            expected=(200, 201),
        )

    def ensure_user(self, username: str, password: str, roles: list[str]) -> None:
        role_params = [("roles", role) for role in roles]
        if self.exists(f"/services/authentication/users/{username}"):
            self.request(
                "POST",
                f"/services/authentication/users/{username}",
                form=[("password", password), *role_params],
            )
            return

        self.request(
            "POST",
            "/services/authentication/users",
            form=[("name", username), ("password", password), *role_params],
            expected=(200, 201),
        )

    def get_dashboard_xml(self, owner: str, app: str, name: str) -> str | None:
        try:
            payload = self.request(
                "GET",
                f"/servicesNS/{owner}/{app}/data/ui/views/{name}",
            )
        except SplunkApiError as error:
            if error.status == 404:
                return None
            raise

        entries = payload.get("entry") or []
        if not entries:
            return None
        return entries[0].get("content", {}).get("eai:data")

    def list_dashboards(self, owner: str, app: str) -> dict[str, str]:
        payload = self.request(
            "GET",
            f"/servicesNS/{owner}/{app}/data/ui/views",
            params={"count": "0"},
        )
        result: dict[str, str] = {}
        for entry in payload.get("entry") or []:
            name = entry.get("name")
            content = entry.get("content", {}).get("eai:data")
            acl = entry.get("acl") or {}
            if (
                name
                and content
                and acl.get("owner") == owner
                and acl.get("app") == app
            ):
                result[name] = content
        return result

    def create_dashboard(self, owner: str, app: str, spec: DashboardSpec) -> None:
        self.request(
            "POST",
            f"/servicesNS/{owner}/{app}/data/ui/views",
            form=[("name", spec.name), ("eai:data", spec.raw_xml)],
            expected=(200, 201),
        )

    def update_dashboard(self, owner: str, app: str, spec: DashboardSpec) -> None:
        self.request(
            "POST",
            f"/servicesNS/{owner}/{app}/data/ui/views/{spec.name}",
            form=[("eai:data", spec.raw_xml)],
        )

    def set_dashboard_acl(self, owner: str, app: str, name: str) -> None:
        self.request(
            "POST",
            f"/servicesNS/{owner}/{app}/data/ui/views/{name}/acl",
            form=[
                ("owner", owner),
                ("sharing", "app"),
                ("perms.read", "*"),
                ("perms.write", "admin,power"),
            ],
        )

    def get_server_info(self) -> Any:
        return self.request("GET", "/services/server/info")


def load_dashboard_specs(dashboard_dir: str | Path) -> list[DashboardSpec]:
    base = Path(dashboard_dir)
    specs = []
    for path in sorted(base.glob("*.xml")):
        raw_xml = path.read_text(encoding="utf-8").strip()
        specs.append(
            DashboardSpec(
                name=path.stem,
                path=path,
                raw_xml=raw_xml,
                canonical_xml=normalize_dashboard_xml(raw_xml),
            )
        )
    return specs


class DashboardPipeline:
    def __init__(
        self,
        *,
        admin_client: SplunkClient,
        service_client: SplunkClient,
        service_account: str,
        service_password: str,
        service_roles: list[str],
        app_name: str,
        app_label: str,
        app_description: str,
    ) -> None:
        self.admin_client = admin_client
        self.service_client = service_client
        self.service_account = service_account
        self.service_password = service_password
        self.service_roles = service_roles
        self.app_name = app_name
        self.app_label = app_label
        self.app_description = app_description

    def wait_for_api(self, attempts: int = 60, sleep_seconds: int = 10) -> None:
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                self.admin_client.get_server_info()
                return
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(sleep_seconds)
        raise RuntimeError(f"Timed out waiting for Splunk management API: {last_error}")

    def bootstrap(self, dashboard_dir: str | Path) -> list[str]:
        self.admin_client.ensure_app(self.app_name, self.app_label, self.app_description)
        self.admin_client.ensure_user(
            self.service_account,
            self.service_password,
            self.service_roles,
        )
        return self.apply(dashboard_dir)

    def apply(self, dashboard_dir: str | Path) -> list[str]:
        changes: list[str] = []
        for spec in load_dashboard_specs(dashboard_dir):
            current_xml = self.service_client.get_dashboard_xml(self.service_account, self.app_name, spec.name)
            if current_xml is None:
                self.service_client.create_dashboard(self.service_account, self.app_name, spec)
                changes.append(f"created:{spec.name}")
            elif normalize_dashboard_xml(current_xml) != spec.canonical_xml:
                self.service_client.update_dashboard(self.service_account, self.app_name, spec)
                changes.append(f"updated:{spec.name}")
            else:
                changes.append(f"unchanged:{spec.name}")

            self.admin_client.set_dashboard_acl(self.service_account, self.app_name, spec.name)
        return changes

    def export_dashboard(self, dashboard_name: str, output_path: str | Path) -> Path:
        xml_text = self.admin_client.get_dashboard_xml(self.service_account, self.app_name, dashboard_name)
        if xml_text is None:
            raise RuntimeError(f"Dashboard {dashboard_name} was not found")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(xml_text.strip() + "\n", encoding="utf-8")
        return output

    def export_all(self, output_dir: str | Path) -> list[Path]:
        exported: list[Path] = []
        base = Path(output_dir)
        base.mkdir(parents=True, exist_ok=True)
        for name, xml_text in sorted(self.admin_client.list_dashboards(self.service_account, self.app_name).items()):
            target = base / f"{name}.xml"
            target.write_text(xml_text.strip() + "\n", encoding="utf-8")
            exported.append(target)
        return exported


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Splunk Dashboard Studio dashboards via REST.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--owner-password")
    parser.add_argument("--owner-roles", default="power")
    parser.add_argument("--app", required=True)
    parser.add_argument("--app-label")
    parser.add_argument("--app-description", default="")
    parser.add_argument("--verify-tls", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=30)

    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--dashboard-dir", required=True)

    apply = subparsers.add_parser("apply")
    apply.add_argument("--dashboard-dir", required=True)

    export = subparsers.add_parser("export")
    export.add_argument("--dashboard", required=True)
    export.add_argument("--output", required=True)

    export_all = subparsers.add_parser("export-all")
    export_all.add_argument("--dashboard-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    owner_password = args.owner_password or args.password
    owner_roles = [role.strip() for role in args.owner_roles.split(",") if role.strip()]

    admin_client = SplunkClient(
        base_url=args.base_url,
        username=args.username,
        password=args.password,
        verify_tls=args.verify_tls,
        timeout_seconds=args.timeout_seconds,
    )
    owner_client = SplunkClient(
        base_url=args.base_url,
        username=args.owner,
        password=owner_password,
        verify_tls=args.verify_tls,
        timeout_seconds=args.timeout_seconds,
    )

    pipeline = DashboardPipeline(
        admin_client=admin_client,
        service_client=owner_client,
        service_account=args.owner,
        service_password=owner_password,
        service_roles=owner_roles,
        app_name=args.app,
        app_label=args.app_label or args.app,
        app_description=args.app_description,
    )

    if args.command == "bootstrap":
        pipeline.wait_for_api()
        for item in pipeline.bootstrap(args.dashboard_dir):
            print(item)
        return 0
    if args.command == "apply":
        for item in pipeline.apply(args.dashboard_dir):
            print(item)
        return 0
    if args.command == "export":
        print(pipeline.export_dashboard(args.dashboard, args.output))
        return 0
    if args.command == "export-all":
        for path in pipeline.export_all(args.dashboard_dir):
            print(path)
        return 0
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
