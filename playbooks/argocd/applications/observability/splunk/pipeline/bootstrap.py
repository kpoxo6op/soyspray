#!/usr/bin/env python3
import os

from splunk_dashboard_pipeline import DashboardPipeline, SplunkClient


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    base_url = env("SPLUNK_BASE_URL")
    admin_username = env("SPLUNK_ADMIN_USERNAME")
    admin_password = env("SPLUNK_ADMIN_PASSWORD")
    service_username = env("SPLUNK_SERVICE_ACCOUNT_USERNAME")
    service_password = env("SPLUNK_SERVICE_ACCOUNT_PASSWORD")
    roles = [role.strip() for role in env("SPLUNK_SERVICE_ACCOUNT_ROLES", "power").split(",") if role.strip()]
    app_name = env("SPLUNK_APP_NAME")
    app_label = env("SPLUNK_APP_LABEL", app_name)
    app_description = env("SPLUNK_APP_DESCRIPTION", "")
    dashboard_dir = env("SPLUNK_DASHBOARD_DIR")
    timeout_seconds = int(env("SPLUNK_TIMEOUT_SECONDS", "30"))

    admin_client = SplunkClient(
        base_url=base_url,
        username=admin_username,
        password=admin_password,
        verify_tls=False,
        timeout_seconds=timeout_seconds,
    )
    service_client = SplunkClient(
        base_url=base_url,
        username=service_username,
        password=service_password,
        verify_tls=False,
        timeout_seconds=timeout_seconds,
    )

    pipeline = DashboardPipeline(
        admin_client=admin_client,
        service_client=service_client,
        service_account=service_username,
        service_password=service_password,
        service_roles=roles,
        app_name=app_name,
        app_label=app_label,
        app_description=app_description,
    )
    pipeline.wait_for_api()
    pipeline.bootstrap(dashboard_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
