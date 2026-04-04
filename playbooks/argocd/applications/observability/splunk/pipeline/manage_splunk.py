#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from splunk_dashboard_pipeline import DashboardPipeline, SplunkClient, load_dashboard_specs, normalize_dashboard_xml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_DASHBOARD_DIR = ROOT / "dashboards"


def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def env_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def wait_for_deployment(namespace: str, timeout_seconds: int = 900) -> None:
    run(
        [
            "kubectl",
            "rollout",
            "status",
            "deployment/splunk",
            "-n",
            namespace,
            f"--timeout={timeout_seconds}s",
        ]
    )


def pick_ready_pod(namespace: str, label_selector: str, timeout_seconds: int = 300) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run(
            [
                "kubectl",
                "get",
                "pods",
                "-n",
                namespace,
                "-l",
                label_selector,
                "-o",
                "json",
            ]
        )
        items = json.loads(result.stdout)["items"]
        ready = []
        for item in items:
            statuses = item.get("status", {}).get("containerStatuses") or []
            if any(status.get("ready") for status in statuses):
                ready.append(item)
        if ready:
            ready.sort(key=lambda item: item["metadata"]["creationTimestamp"], reverse=True)
            return ready[0]["metadata"]["name"]
        time.sleep(5)
    raise RuntimeError("Timed out waiting for a Ready Splunk pod")


@contextmanager
def port_forward(namespace: str, pod_name: str, local_port: int, remote_port: int):
    command = [
        "kubectl",
        "port-forward",
        "-n",
        namespace,
        f"pod/{pod_name}",
        f"{local_port}:{remote_port}",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout else ""
                raise RuntimeError(f"port-forward exited early: {output}")
            time.sleep(1)
            break
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


class OperatorSession:
    def __init__(self, config: dict[str, str]) -> None:
        self.config = config
        self.dashboard_dir = Path(config.get("SPLUNK_DASHBOARD_DIR", str(DEFAULT_DASHBOARD_DIR)))

    @contextmanager
    def pipeline(self):
        namespace = self.config["SPLUNK_NAMESPACE"]
        label_selector = self.config["SPLUNK_POD_LABEL_SELECTOR"]
        local_port = int(self.config["SPLUNK_MGMT_LOCAL_PORT"])
        remote_port = int(self.config["SPLUNK_MGMT_REMOTE_PORT"])

        wait_for_deployment(namespace)
        pod_name = pick_ready_pod(namespace, label_selector)

        with port_forward(namespace, pod_name, local_port, remote_port):
            base_url = f"{self.config['SPLUNK_MGMT_SCHEME']}://{self.config['SPLUNK_MGMT_HOST']}:{local_port}"
            verify_tls = env_bool(self.config.get("SPLUNK_VERIFY_TLS", "false"))
            admin_client = SplunkClient(
                base_url=base_url,
                username=self.config["SPLUNK_ADMIN_USERNAME"],
                password=self.config["SPLUNK_ADMIN_PASSWORD"],
                verify_tls=verify_tls,
                timeout_seconds=30,
            )
            service_client = SplunkClient(
                base_url=base_url,
                username=self.config["SPLUNK_SERVICE_ACCOUNT_USERNAME"],
                password=self.config["SPLUNK_SERVICE_ACCOUNT_PASSWORD"],
                verify_tls=verify_tls,
                timeout_seconds=30,
            )
            pipeline = DashboardPipeline(
                admin_client=admin_client,
                service_client=service_client,
                service_account=self.config["SPLUNK_SERVICE_ACCOUNT_USERNAME"],
                service_password=self.config["SPLUNK_SERVICE_ACCOUNT_PASSWORD"],
                service_roles=[role.strip() for role in self.config["SPLUNK_SERVICE_ACCOUNT_ROLES"].split(",") if role.strip()],
                app_name=self.config["SPLUNK_APP_NAME"],
                app_label=self.config["SPLUNK_APP_LABEL"],
                app_description=self.config["SPLUNK_APP_DESCRIPTION"],
            )
            pipeline.wait_for_api(attempts=30, sleep_seconds=5)
            yield pipeline


def reset_managed_state(pipeline: DashboardPipeline) -> None:
    if pipeline.admin_client.exists(f"/services/apps/local/{pipeline.app_name}"):
        pipeline.admin_client.request("DELETE", f"/services/apps/local/{pipeline.app_name}", expected=(200,))
    if pipeline.admin_client.exists(f"/services/authentication/users/{pipeline.service_account}"):
        pipeline.admin_client.request("DELETE", f"/services/authentication/users/{pipeline.service_account}", expected=(200,))


def verify_managed_state(pipeline: DashboardPipeline, dashboard_dir: Path) -> None:
    user_payload = pipeline.admin_client.request("GET", f"/services/authentication/users/{pipeline.service_account}")
    if user_payload["entry"][0]["name"] != pipeline.service_account:
        raise RuntimeError("Service account verification failed")

    app_payload = pipeline.admin_client.request("GET", f"/services/apps/local/{pipeline.app_name}")
    if app_payload["entry"][0]["name"] != pipeline.app_name:
        raise RuntimeError("App verification failed")

    expected = {spec.name: spec.canonical_xml for spec in load_dashboard_specs(dashboard_dir)}
    live = pipeline.admin_client.list_dashboards(pipeline.service_account, pipeline.app_name)
    for name, expected_xml in expected.items():
        if name not in live:
            raise RuntimeError(f"Missing dashboard {name}")
        if normalize_dashboard_xml(live[name]) != expected_xml:
            raise RuntimeError(f"Dashboard drift detected for {name}")
        acl_payload = pipeline.admin_client.request(
            "GET",
            f"/servicesNS/{pipeline.service_account}/{pipeline.app_name}/data/ui/views/{name}",
        )
        acl = acl_payload["entry"][0]["acl"]
        if acl["owner"] != pipeline.service_account or acl["app"] != pipeline.app_name or acl["sharing"] != "app":
            raise RuntimeError(f"ACL mismatch for {name}: {acl}")


def run_e2e(session: OperatorSession) -> None:
    with session.pipeline() as pipeline:
        reset_managed_state(pipeline)
        changes = pipeline.bootstrap(session.dashboard_dir)
        print("\n".join(changes))
        verify_managed_state(pipeline, session.dashboard_dir)

        with tempfile.TemporaryDirectory(prefix="splunk-export-") as tmpdir:
            exported = pipeline.export_all(tmpdir)
            exported_names = sorted(path.stem for path in exported)
            expected_names = sorted(spec.name for spec in load_dashboard_specs(session.dashboard_dir))
            if exported_names != expected_names:
                raise RuntimeError(f"Export mismatch: {exported_names} != {expected_names}")
            for expected_spec in load_dashboard_specs(session.dashboard_dir):
                exported_text = Path(tmpdir, f"{expected_spec.name}.xml").read_text(encoding="utf-8")
                if normalize_dashboard_xml(exported_text) != expected_spec.canonical_xml:
                    raise RuntimeError(f"Export drift detected for {expected_spec.name}")

        print("e2e-ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate Splunk dashboard state from repo code using .env.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("apply")
    subparsers.add_parser("reset")
    subparsers.add_parser("e2e")
    export_all = subparsers.add_parser("export-all")
    export_all.add_argument("--output-dir", default=str(DEFAULT_DASHBOARD_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_dotenv(Path(args.env_file))
    session = OperatorSession(config)

    if args.command == "apply":
        with session.pipeline() as pipeline:
            for change in pipeline.bootstrap(session.dashboard_dir):
                print(change)
        return 0

    if args.command == "reset":
        with session.pipeline() as pipeline:
            reset_managed_state(pipeline)
            print("reset-ok")
        return 0

    if args.command == "e2e":
        run_e2e(session)
        return 0

    if args.command == "export-all":
        output_dir = Path(args.output_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        with session.pipeline() as pipeline:
            for path in pipeline.export_all(output_dir):
                print(path)
        return 0

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
